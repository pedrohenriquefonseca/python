"""
fetcher.py — Job batch que coleta todos os dados do PWA e salva em data/*.json.

Executado pelo Windows Task Scheduler (9:15, 14:15, 16:45 todos os dias).
Roda standalone — não precisa do Flask, não tem servidor.

Coleta incremental: a lista de projetos é sempre atualizada (é barata e traz o
LastPublishedDate de todos), mas as tarefas — o grosso do tempo — só são
buscadas nos projetos republicados desde a última coleta bem-sucedida. Rode com
`--full` para forçar a recoleta de tudo.

Saída:
  data/projects.json     — lista de todos os projetos
  data/tasks_<pid>.json  — tarefas de cada projeto
  data/fetch_state.json  — publicação já coletada com sucesso, por projeto
  data/last_update.json  — timestamp + status do último run
  data/fetch_progress.json — andamento do run em curso (lido pela barra do dashboard)
  data/fetcher.log       — log rotativo (até 1MB)
"""
import json
import logging
import logging.handlers
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import pwa_client

# ── Setup ─────────────────────────────────────────────────────────────────────
HERE          = Path(__file__).parent
DATA_DIR      = HERE / "data"
LOG_FILE      = DATA_DIR / "fetcher.log"
STATE_FILE    = DATA_DIR / "fetch_state.json"
PROGRESS_FILE = DATA_DIR / "fetch_progress.json"
DATA_DIR.mkdir(exist_ok=True)

handler_file = logging.handlers.RotatingFileHandler(
    LOG_FILE, maxBytes=1_000_000, backupCount=2, encoding="utf-8"
)
handler_file.setFormatter(logging.Formatter(
    "%(asctime)s  %(levelname)-7s  %(name)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
))
logging.basicConfig(
    level=logging.INFO,
    handlers=[handler_file, logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("fetcher")


# ── Persistência ──────────────────────────────────────────────────────────────

def _write_json(path: Path, data) -> None:
    """Escreve JSON atomicamente (escreve em .tmp e move)."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def _save_status(ok: bool, started: float, **extra) -> None:
    """Grava data/last_update.json com sumário do run."""
    status = {
        "ok":             ok,
        "started_at":     datetime.fromtimestamp(started).isoformat(timespec="seconds"),
        "finished_at":    datetime.now().isoformat(timespec="seconds"),
        "duration_secs":  round(time.time() - started, 1),
        **extra,
    }
    _write_json(DATA_DIR / "last_update.json", status)


# ── Andamento (barra de progresso do dashboard) ───────────────────────────────

def _save_progress(run_id: str, fase: str, rotulo: str,
                   feito: int = 0, total: int = 0, ativo: bool = True) -> None:
    """Grava data/fetch_progress.json com o andamento do run em curso.

    `total = 0` significa fase sem denominador conhecido (autenticação, lista de
    projetos, limpeza): o dashboard mostra a barra indeterminada. `run_id` é o
    carimbo de início — é ele que distingue este run de um arquivo esquecido de
    uma coleta anterior.

    Andamento é acessório: se a escrita falhar, a coleta continua. Perder a barra
    é irrelevante perto de perder o snapshot.
    """
    try:
        _write_json(PROGRESS_FILE, {
            "run_id":        run_id,
            "fase":          fase,
            "rotulo":        rotulo,
            "feito":         feito,
            "total":         total,
            "ativo":         ativo,
            "atualizado_em": datetime.now().isoformat(timespec="seconds"),
        })
    except Exception as exc:
        log.debug("Falha ao gravar andamento (%s): %s", fase, exc)


# ── Estado da coleta incremental ──────────────────────────────────────────────

def _load_state() -> dict:
    """Publicação de cada projeto já coletada com sucesso.

    Fica separado do projects.json de propósito: aquele é sobrescrito a cada
    run, inclusive quando a coleta das tarefas falha. Este só avança quando as
    tarefas foram realmente gravadas — assim uma falha é reprocessada no run
    seguinte em vez de ser dada como feita.
    """
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8")).get("projects", {})
    except Exception as exc:
        log.warning("fetch_state.json ilegível (%s) — recoletando tudo.", exc)
        return {}


def _save_state(projects: dict) -> None:
    _write_json(STATE_FILE, {
        "atualizado_em": datetime.now().isoformat(timespec="seconds"),
        "projects":      projects,
    })


def _precisa_coletar(p: dict, state: dict, forcar: bool) -> tuple[bool, str]:
    """Decide se as tarefas do projeto precisam ser buscadas do servidor."""
    pid = p["id"]
    if forcar:
        return True, "recoleta forçada"
    if not (DATA_DIR / f"tasks_{pid}.json").exists():
        return True, "sem snapshot local"
    publicado = p.get("publicadoEm")
    if not publicado:
        # Sem carimbo de publicação não há como detectar mudança — na dúvida,
        # coleta (é o caso de projeto nunca publicado ou campo indisponível).
        return True, "sem data de publicação"
    anterior = (state.get(pid) or {}).get("publicadoEm")
    if anterior != publicado:
        return True, f"republicado ({anterior or '—'} → {publicado})"
    return False, ""


# ── Fetch ─────────────────────────────────────────────────────────────────────

def _fetch_tasks_safe(p: dict) -> tuple[str, int, str | None]:
    """Wrapper de fetch_tasks com retry — projetos grandes às vezes dão timeout.

    Devolve (pid, nº de tarefas, erro).
    """
    pid, name = p["id"], p["name"]
    last_exc = None
    for attempt in (1, 2, 3):
        try:
            tasks = pwa_client.fetch_tasks(pid)
            _write_json(DATA_DIR / f"tasks_{pid}.json", tasks)
            return pid, len(tasks), None
        except Exception as exc:
            last_exc = exc
            log.warning("Tentativa %d/3 falhou em '%s' (%s): %s",
                        attempt, name, pid[:8], exc)
            time.sleep(2 * attempt)  # backoff
    return pid, 0, str(last_exc)


def main(forcar: bool = False, run_id: str | None = None) -> int:
    started = time.time()
    # Quando o run nasce do botão do dashboard, o Flask já gravou um andamento
    # inicial e passa o mesmo identificador aqui — é ele que amarra os dois
    # arquivos ao mesmo run e faz o browser ignorar sobras de coletas antigas.
    run_id  = run_id or datetime.fromtimestamp(started).isoformat(timespec="seconds")
    log.info("=" * 60)
    log.info("Fetcher iniciado — %s%s", datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
             "  [--full]" if forcar else "")

    # 1) Verifica autenticação
    _save_progress(run_id, "autenticando", "Verificando autenticação…")
    if not pwa_client.is_authenticated():
        log.error("Sem token MSAL válido — rode: python -c "
                  "\"import pwa_client; pwa_client.start_device_flow()\"")
        _save_status(False, started, error="no_token", projects=0, tasks=0)
        _save_progress(run_id, "erro", "Sem token válido — refaça o login no PWA",
                       ativo=False)
        return 1

    # 2) Busca projetos (sempre — é barato e traz o LastPublishedDate de todos)
    _save_progress(run_id, "projetos", "Buscando lista de projetos…")
    try:
        projects = pwa_client.fetch_projects()
        _write_json(DATA_DIR / "projects.json", projects)
        log.info("Projetos salvos: %d", len(projects))
    except Exception as exc:
        log.exception("Erro ao buscar projetos:")
        _save_status(False, started, error=str(exc), projects=0, tasks=0)
        _save_progress(run_id, "erro", f"Falha ao buscar projetos: {exc}", ativo=False)
        return 2

    # 3) Decide quem precisa de recoleta das tarefas
    state = _load_state()
    a_coletar, reaproveitados = [], []
    for p in projects:
        precisa, motivo = _precisa_coletar(p, state, forcar)
        if precisa:
            a_coletar.append(p)
            log.info("  coletar  %-42s (%s)", p["name"][:42], motivo)
        else:
            reaproveitados.append(p)
    log.info("Tarefas: %d projeto(s) a coletar, %d reaproveitado(s) do snapshot.",
             len(a_coletar), len(reaproveitados))

    # 4) Busca tarefas apenas dos projetos republicados (paralelo).
    #    Maiores primeiro: evita o projeto grande sozinho no fim da fila.
    total_tasks = sum((state.get(p["id"]) or {}).get("tarefas", 0) for p in reaproveitados)
    errors      = []
    ordem = sorted(a_coletar,
                   key=lambda p: (state.get(p["id"]) or {}).get("tarefas", 10 ** 6),
                   reverse=True)

    # A barra do dashboard mede esta fase: é aqui que o tempo do run vai. O
    # denominador são os projetos a coletar — os reaproveitados entram só como
    # nota no rótulo, para o número não parecer pequeno demais.
    sufixo = f" · {len(reaproveitados)} reaproveitado(s)" if reaproveitados else ""

    def _rotulo_tarefas(feito: int) -> str:
        return f"Tarefas: {feito} de {len(a_coletar)} projeto(s){sufixo}"

    concluidos = 0
    _save_progress(run_id, "tarefas", _rotulo_tarefas(0), 0, len(a_coletar))

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(_fetch_tasks_safe, p): p for p in ordem}
        for fut in as_completed(futures):
            pid, n_tasks, err = fut.result()
            p = futures[fut]
            concluidos += 1
            _save_progress(run_id, "tarefas", _rotulo_tarefas(concluidos),
                           concluidos, len(a_coletar))
            if err:
                errors.append({"pid": pid, "error": err})
                continue
            total_tasks += n_tasks
            # Só aqui o estado avança: falha volta a ser tentada no próximo run.
            state[pid] = {
                "publicadoEm": p.get("publicadoEm"),
                "coletadoEm":  datetime.now().isoformat(timespec="seconds"),
                "tarefas":     n_tasks,
            }

    log.info("Tarefas: %d no total (%d projeto(s) recoletado(s))",
             total_tasks, len(a_coletar) - len(errors))
    if errors:
        log.warning("Falhas: %d projetos", len(errors))

    # 5) Limpa arquivos de projetos que não existem mais
    _save_progress(run_id, "limpeza", "Organizando snapshot…",
                   len(a_coletar), len(a_coletar))
    valid_ids = {p["id"] for p in projects}
    for padrao, rotulo in (("tasks_*.json", "tarefas"),
                           ("report_base_*.json", "base do report")):
        prefixo = padrao.split("*")[0]
        for f in DATA_DIR.glob(padrao):
            pid = f.stem.replace(prefixo, "")
            if pid not in valid_ids:
                log.info("Removendo %s (%s de projeto inexistente)", f.name, rotulo)
                f.unlink()
    for pid in [pid for pid in state if pid not in valid_ids]:
        del state[pid]

    _save_state(state)

    # 6) Grava status final
    _save_status(
        True, started,
        projects=len(projects),
        tasks=total_tasks,
        coletados=len(a_coletar) - len(errors),
        reaproveitados=len(reaproveitados),
        errors=errors,
    )
    duracao = time.time() - started
    falhas  = f" · {len(errors)} falha(s)" if errors else ""
    _save_progress(
        run_id, "concluido",
        f"Concluído em {duracao:.0f}s · {len(projects)} proj · "
        f"{total_tasks} tarefas{falhas}",
        len(a_coletar), len(a_coletar), ativo=False,
    )
    log.info("Fetcher concluído em %.1fs.", duracao)
    return 0


if __name__ == "__main__":
    _rid = None
    if "--run-id" in sys.argv:
        _i = sys.argv.index("--run-id")
        if _i + 1 < len(sys.argv):
            _rid = sys.argv[_i + 1]
    sys.exit(main(forcar="--full" in sys.argv, run_id=_rid))

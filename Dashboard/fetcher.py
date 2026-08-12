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

import historico
import pwa_client

# ── Setup ─────────────────────────────────────────────────────────────────────
HERE       = Path(__file__).parent
DATA_DIR   = HERE / "data"
LOG_FILE   = DATA_DIR / "fetcher.log"
STATE_FILE = DATA_DIR / "fetch_state.json"
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

def _fetch_tasks_safe(p: dict) -> tuple[str, int, str | None, str | None]:
    """Wrapper de fetch_tasks com retry — projetos grandes às vezes dão timeout.

    Devolve (pid, nº de tarefas, erro, versão registrada no histórico).
    """
    pid, name = p["id"], p["name"]
    last_exc = None
    for attempt in (1, 2, 3):
        try:
            tasks = pwa_client.fetch_tasks(pid)
            _write_json(DATA_DIR / f"tasks_{pid}.json", tasks)
            # O histórico é acessório: se falhar, a coleta não pode cair junto.
            versao = None
            try:
                versao = historico.registrar(pid, p, tasks)
            except Exception as exc:
                log.warning("Falha ao versionar '%s': %s", name, exc)
            return pid, len(tasks), None, versao
        except Exception as exc:
            last_exc = exc
            log.warning("Tentativa %d/3 falhou em '%s' (%s): %s",
                        attempt, name, pid[:8], exc)
            time.sleep(2 * attempt)  # backoff
    return pid, 0, str(last_exc), None


def main(forcar: bool = False) -> int:
    started = time.time()
    log.info("=" * 60)
    log.info("Fetcher iniciado — %s%s", datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
             "  [--full]" if forcar else "")

    # O histórico grava sempre ao lado dos snapshots: quem redireciona a saída
    # do fetcher redireciona os dois, sem precisar saber que existem dois módulos.
    historico.DATA_DIR = DATA_DIR

    # 1) Verifica autenticação
    if not pwa_client.is_authenticated():
        log.error("Sem token MSAL válido — rode 'python reauth.py' manualmente.")
        _save_status(False, started, error="no_token", projects=0, tasks=0)
        return 1

    # 2) Busca projetos (sempre — é barato e traz o LastPublishedDate de todos)
    try:
        projects = pwa_client.fetch_projects()
        _write_json(DATA_DIR / "projects.json", projects)
        log.info("Projetos salvos: %d", len(projects))
    except Exception as exc:
        log.exception("Erro ao buscar projetos:")
        _save_status(False, started, error=str(exc), projects=0, tasks=0)
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
    versionados = 0
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(_fetch_tasks_safe, p): p for p in ordem}
        for fut in as_completed(futures):
            pid, n_tasks, err, versao = fut.result()
            p = futures[fut]
            if err:
                errors.append({"pid": pid, "error": err})
                continue
            total_tasks += n_tasks
            versionados += 1 if versao else 0
            # Só aqui o estado avança: falha volta a ser tentada no próximo run.
            state[pid] = {
                "publicadoEm": p.get("publicadoEm"),
                "coletadoEm":  datetime.now().isoformat(timespec="seconds"),
                "tarefas":     n_tasks,
            }

    log.info("Tarefas: %d no total (%d projeto(s) recoletado(s), %d nova(s) versão(ões))",
             total_tasks, len(a_coletar) - len(errors), versionados)
    if errors:
        log.warning("Falhas: %d projetos", len(errors))

    # 5) Limpa arquivos de projetos que não existem mais
    valid_ids = {p["id"] for p in projects}
    for padrao, rotulo in (("tasks_*.json", "tarefas"), ("history_*.json", "histórico")):
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
        versionados=versionados,
        errors=errors,
    )
    log.info("Fetcher concluído em %.1fs.", time.time() - started)
    return 0


if __name__ == "__main__":
    sys.exit(main(forcar="--full" in sys.argv))

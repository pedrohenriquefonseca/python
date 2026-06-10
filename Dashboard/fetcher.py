"""
fetcher.py — Job batch que coleta todos os dados do PWA e salva em data/*.json.

Executado pelo Windows Task Scheduler (9:15, 14:15, 16:45 todos os dias).
Roda standalone — não precisa do Flask, não tem servidor.

Saída:
  data/projects.json     — lista de todos os projetos
  data/tasks_<pid>.json  — tarefas de cada projeto
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

import pwa_client

# ── Setup ─────────────────────────────────────────────────────────────────────
HERE     = Path(__file__).parent
DATA_DIR = HERE / "data"
LOG_FILE = DATA_DIR / "fetcher.log"
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


# ── Fetch ─────────────────────────────────────────────────────────────────────

def _fetch_tasks_safe(pid: str, name: str) -> tuple[str, int, str | None]:
    """Wrapper de fetch_tasks com retry — projetos grandes às vezes dão timeout."""
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


def main() -> int:
    started = time.time()
    log.info("=" * 60)
    log.info("Fetcher iniciado — %s", datetime.now().strftime("%d/%m/%Y %H:%M:%S"))

    # 1) Verifica autenticação
    if not pwa_client.is_authenticated():
        log.error("Sem token MSAL válido — rode 'python reauth.py' manualmente.")
        _save_status(False, started, error="no_token", projects=0, tasks=0)
        return 1

    # 2) Busca projetos
    try:
        projects = pwa_client.fetch_projects()
        _write_json(DATA_DIR / "projects.json", projects)
        log.info("Projetos salvos: %d", len(projects))
    except Exception as exc:
        log.exception("Erro ao buscar projetos:")
        _save_status(False, started, error=str(exc), projects=0, tasks=0)
        return 2

    # 3) Busca tarefas de cada projeto (paralelo)
    total_tasks = 0
    errors      = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {
            pool.submit(_fetch_tasks_safe, p["id"], p["name"]): p
            for p in projects
        }
        for fut in as_completed(futures):
            pid, n_tasks, err = fut.result()
            if err:
                errors.append({"pid": pid, "error": err})
            else:
                total_tasks += n_tasks

    log.info("Tarefas salvas: %d (em %d projetos)", total_tasks, len(projects) - len(errors))
    if errors:
        log.warning("Falhas: %d projetos", len(errors))

    # 4) Limpa tasks_*.json de projetos que não existem mais
    valid_ids = {p["id"] for p in projects}
    for f in DATA_DIR.glob("tasks_*.json"):
        pid = f.stem.replace("tasks_", "")
        if pid not in valid_ids:
            log.info("Removendo %s (projeto inexistente)", f.name)
            f.unlink()

    # 5) Grava status final
    _save_status(
        True, started,
        projects=len(projects),
        tasks=total_tasks,
        errors=errors,
    )
    log.info("Fetcher concluído em %.1fs.", time.time() - started)
    return 0


if __name__ == "__main__":
    sys.exit(main())

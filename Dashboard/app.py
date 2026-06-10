"""
Servidor Flask para o PMO Dashboard.

Não chama mais o PWA diretamente — lê os snapshots gerados por fetcher.py.
Tudo do dashboard fica instantâneo (lê de disco).

Para atualizar os dados manualmente: POST /api/refresh (chama fetcher.py).
Para fluxo automático: Windows Task Scheduler roda fetcher.py 3x/dia.
"""
import io
import json
import logging
import os
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

# ── SSE keepalive (encerra servidor quando o browser fecha) ──────────────────
_clients      = 0
_clients_lock = threading.Lock()

import matplotlib
matplotlib.use('Agg')

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

import pwa_client

# ── Scripts das ferramentas (subpastas locais por função) ─────────────────────
_HERE_DIR = Path(__file__).parent

sys.path.insert(0, str(_HERE_DIR / 'report_semanal'))
sys.path.insert(0, str(_HERE_DIR / 'cronograma_alocacao'))
sys.path.insert(0, str(_HERE_DIR / 'ferias'))

from Report import gerar_relatorio_web_json
from gantt_projetos import gerar_para_web_json as _gerar_projetos_web_json
from gantt_clientes import (
    gerar_para_web_json as _gerar_equipe_web_json,
    verificar_recursos_desconhecidos_json,
)
import ferias as ferias_mod

ferias_mod.DB_PATH = str(_HERE_DIR / 'ferias' / 'ferias_db.json')
_DESEMBOLSO_DIR = _HERE_DIR / 'desembolso'

# ── Setup ─────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

HERE     = Path(__file__).parent
DATA_DIR = HERE / "data"

app = Flask(__name__, static_folder=str(HERE))
CORS(app)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _read_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        log.error("Erro lendo %s: %s", path, exc)
        return default


# Projeto mestre consolidado de alocação da equipe (único com recursos
# individuais por tarefa). Alimenta os gantts de Equipe Interna e Fornecedores.
MASTER_PROJECT_NAME = "Cronograma Macro Horizontes"


def _is_master(projeto: dict) -> bool:
    return (projeto.get("name") or "").strip().casefold() == MASTER_PROJECT_NAME.casefold()


def _master_tasks() -> list:
    """Tarefas do projeto mestre consolidado (com nomes individuais)."""
    projetos = _read_json(DATA_DIR / "projects.json", []) or []
    mestre = next((p for p in projetos if _is_master(p)), None)
    if not mestre or not mestre.get("id"):
        return []
    return _read_json(DATA_DIR / f"tasks_{mestre['id']}.json", []) or []


# ── Arquivos estáticos ────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory(str(HERE), "index.html")


@app.route("/<path:filename>")
def static_files(filename):
    return send_from_directory(str(HERE), filename)


# ── Auth API (mantida só para login inicial / reauth manual) ──────────────────

@app.route("/api/auth/start", methods=["POST"])
def auth_start():
    try:
        return jsonify(pwa_client.start_device_flow())
    except Exception as exc:
        log.error("Erro ao iniciar device flow: %s", exc)
        return jsonify({"error": str(exc)}), 500


@app.route("/api/auth/poll")
def auth_poll():
    try:
        token = pwa_client.poll_device_flow()
        return jsonify({"authenticated": bool(token)})
    except Exception as exc:
        log.error("Erro no poll: %s", exc)
        return jsonify({"error": str(exc)}), 500


@app.route("/api/auth/status")
def auth_status():
    return jsonify({"authenticated": pwa_client.is_authenticated()})


# ── Dados (lidos do snapshot em disco) ────────────────────────────────────────

@app.route("/api/projects")
def projects():
    data = _read_json(DATA_DIR / "projects.json", None)
    if data is None:
        return jsonify({
            "error": "Nenhum snapshot disponível. Rode fetcher.py ou aguarde "
                     "a próxima execução agendada.",
        }), 503
    # O projeto mestre consolidado só deve aparecer na aba Cronogramas de Alocação.
    if isinstance(data, list):
        data = [p for p in data if not _is_master(p)]
    return jsonify(data)


@app.route("/api/tasks/<project_id>")
def tasks(project_id: str):
    data = _read_json(DATA_DIR / f"tasks_{project_id}.json", None)
    if data is None:
        return jsonify({"error": "Tarefas não disponíveis para esse projeto."}), 404
    return jsonify(data)


@app.route("/api/status")
def status():
    """Retorna timestamp e info do último fetch (lido por index.html)."""
    return jsonify(_read_json(DATA_DIR / "last_update.json", {
        "ok": False,
        "started_at": None,
        "finished_at": None,
        "projects": 0,
        "tasks": 0,
    }))


@app.route("/api/keepalive")
def keepalive():
    """SSE persistente — queda da conexão indica fechamento do browser."""
    from flask import Response, stream_with_context

    global _clients

    with _clients_lock:
        _clients += 1
    log.info("Browser conectado (total: %d)", _clients)

    def stream():
        global _clients
        try:
            while True:
                yield "data: ok\n\n"
                time.sleep(20)
        finally:
            with _clients_lock:
                _clients -= 1
            log.info("Browser desconectado (total: %d)", _clients)

            def _maybe_exit():
                time.sleep(1)          # aguarda possível reload da página
                if _clients <= 0:
                    log.info("Sem browsers ativos — encerrando em 1 s…")
                    time.sleep(1)
                    os._exit(0)

            threading.Thread(target=_maybe_exit, daemon=True).start()

    return Response(
        stream_with_context(stream()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.route("/api/refresh", methods=["POST"])
def refresh():
    """Dispara o fetcher manualmente em background. Útil para forçar refresh."""
    try:
        subprocess.Popen(
            [sys.executable, str(HERE / "fetcher.py")],
            cwd=str(HERE),
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        return jsonify({"started": True})
    except Exception as exc:
        log.error("Erro ao iniciar fetcher: %s", exc)
        return jsonify({"error": str(exc)}), 500


# ── Ferramentas (GUI integrado) ───────────────────────────────────────────────

@app.route("/api/report-json", methods=["POST"])
def api_report_json():
    """Report Semanal 2.0 — gera o relatório direto do snapshot JSON do PWA,
    sem upload de Excel. Recebe {project_id, nome_projeto} e lê o
    data/tasks_<project_id>.json já usado pelos dashboards."""
    try:
        data       = request.get_json(silent=True) or {}
        project_id = (data.get("project_id") or "").strip()
        nome       = (data.get("nome_projeto") or "").strip()
        if not project_id:
            return jsonify({"error": "Selecione um projeto."}), 400
        tarefas = _read_json(DATA_DIR / f"tasks_{project_id}.json", None)
        if tarefas is None:
            return jsonify({"error": "Tarefas não disponíveis para esse projeto no snapshot."}), 404
        if not nome:
            projetos = _read_json(DATA_DIR / "projects.json", []) or []
            match = next((p for p in projetos if str(p.get("id")) == project_id), None)
            nome = (match or {}).get("name", "") or "Projeto"
        conteudo, nome_arq = gerar_relatorio_web_json(tarefas, nome)
        return jsonify({"success": True, "content": conteudo, "filename": nome_arq})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/desembolso", methods=["POST"])
def api_desembolso():
    try:
        arq   = request.files.get("arquivo")
        nome  = request.form.get("nome_projeto", "").strip()
        corte = int(request.form.get("dia_corte", 25))
        if not arq or not nome:
            return jsonify({"error": "Arquivo e nome do projeto são obrigatórios"}), 400
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as f:
            arq.save(f)
            tmp = f.name
        runner = str(_DESEMBOLSO_DIR / "_desembolso_runner.py")
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        proc = subprocess.Popen(
            [sys.executable, runner, tmp, nome, str(corte)],
            stderr=subprocess.PIPE, stdout=subprocess.PIPE, env=env,
        )
        time.sleep(1.5)
        if proc.poll() is not None:
            stderr = proc.stderr.read().decode("utf-8", errors="replace").strip()
            ultima = stderr.split("\n")[-1].strip()
            msg = ultima.split(": ", 1)[1] if ": " in ultima else ultima
            return jsonify({"error": msg}), 500
        return jsonify({"success": True, "message": "Gráfico aberto em nova janela!"})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


# ── Cronogramas de Alocação (direto do snapshot JSON do PWA) ──────────────────

@app.route("/api/cronograma/projetos", methods=["POST"])
def api_cronograma_projetos():
    """Projetos por Cliente — hierarquia nível 1/2 do projeto mestre consolidado."""
    try:
        tarefas = _master_tasks()
        if not tarefas:
            return jsonify({"error": "Projeto mestre não encontrado no snapshot."}), 404
        img = _gerar_projetos_web_json(tarefas)
        return jsonify({"success": True, "image": img})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/cronograma/verificar", methods=["POST"])
def api_cronograma_verificar():
    """Recursos das tarefas do projeto mestre ainda sem grupo definido."""
    try:
        desconhecidos = verificar_recursos_desconhecidos_json(_master_tasks())
        return jsonify({"desconhecidos": desconhecidos})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/cronograma/equipe", methods=["POST"])
def api_cronograma_equipe():
    """Fornecedores / Equipe Interna — alocação a partir das tarefas do projeto mestre."""
    try:
        data = request.get_json(silent=True) or {}
        grupos_novos = data.get("grupos_novos") or None
        results = _gerar_equipe_web_json(_master_tasks(), grupos_novos=grupos_novos)
        return jsonify({"success": True, **results})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/cronograma/clientes", methods=["POST"])
def api_cronograma_clientes():
    """Alias de /api/cronograma/equipe (mesmo motor gera 'horizontes' e 'fornecedores')."""
    try:
        data = request.get_json(silent=True) or {}
        grupos_novos = data.get("grupos_novos") or None
        results = _gerar_equipe_web_json(_master_tasks(), grupos_novos=grupos_novos)
        return jsonify({"success": True, **results})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/ferias/funcionarios", methods=["GET"])
def api_ferias_funcionarios():
    return jsonify(ferias_mod.listar_funcionarios())


@app.route("/api/ferias/consultar", methods=["POST"])
def api_ferias_consultar():
    data = request.get_json(silent=True) or {}
    nome = data.get("nome", "").strip()
    if not nome:
        return jsonify({"erro": "Nome é obrigatório."}), 400
    return jsonify(ferias_mod.consultar_funcionario(nome))


@app.route("/api/ferias/registrar", methods=["POST"])
def api_ferias_registrar():
    data     = request.get_json(silent=True) or {}
    nome     = data.get("nome", "").strip()
    inicio   = data.get("inicio", "").strip()
    fim      = data.get("fim", "").strip()
    admissao = (data.get("admissao", "") or "").strip() or None
    if not all([nome, inicio, fim]):
        return jsonify({"erro": "Nome, início e fim são obrigatórios."}), 400
    return jsonify(ferias_mod.registrar_ferias(nome, inicio, fim, admissao))


@app.route("/api/ferias/cancelar", methods=["POST"])
def api_ferias_cancelar():
    data     = request.get_json(silent=True) or {}
    nome     = data.get("nome", "").strip()
    entry_id = data.get("id", "").strip()
    if not all([nome, entry_id]):
        return jsonify({"erro": "Nome e id são obrigatórios."}), 400
    return jsonify(ferias_mod.cancelar_ferias(nome, entry_id))


# ── Inicialização ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import webbrowser
    print("\n" + "=" * 60)
    print("  PMO Dashboard — Horizontes")
    print(f"  Dados:   {DATA_DIR}")
    print("  Acesse:  http://localhost:5000")
    print("=" * 60 + "\n")
    threading.Timer(1.2, lambda: webbrowser.open("http://localhost:5000")).start()
    app.run(debug=False, port=5000, use_reloader=False, threaded=True)

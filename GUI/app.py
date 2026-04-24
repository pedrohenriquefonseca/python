"""
Horizontes — Portal de Ferramentas
Servidor Flask local que importa os scripts existentes da pasta Projetos.
Execute:  python app.py
Acesse:   http://localhost:5000
"""
import os, sys, io, subprocess, threading, tempfile, webbrowser, time

# Caminhos
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJ_DIR = os.path.dirname(BASE_DIR)  # pasta Projetos/

# Matplotlib backend sem janela (antes de qualquer import de pyplot)
import matplotlib
matplotlib.use('Agg')

# Adicionar pastas dos scripts ao path para importação
sys.path.insert(0, os.path.join(PROJ_DIR, 'Report Semanal'))
sys.path.insert(0, os.path.join(PROJ_DIR, 'Cronograma de Equipe'))

# Importar funções dos scripts originais
from Report import gerar_relatorio_web
from gantt_projetos import gerar_para_web as gerar_projetos_web
from gantt_clientes import gerar_para_web as gerar_equipe_web

from flask import Flask, render_template, request, jsonify, send_file, Response, stream_with_context

app = Flask(__name__,
            template_folder=os.path.join(BASE_DIR, 'templates'),
            static_folder=os.path.join(BASE_DIR, 'static'))
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50 MB

# ══════════════════════════════════════════════════════════════
#  ENCERRAMENTO AUTOMÁTICO  (detecta fechamento do browser via SSE)
# ══════════════════════════════════════════════════════════════
_lock              = threading.Lock()
_conexoes_ativas   = 0
_timer_encerramento = None

def _encerrar():
    print('\nPortal encerrado — browser fechado.')
    os._exit(0)

def _agendar_encerramento():
    global _timer_encerramento
    _timer_encerramento = threading.Timer(0.5, _encerrar)
    _timer_encerramento.daemon = True
    _timer_encerramento.start()

def _cancelar_encerramento():
    global _timer_encerramento
    if _timer_encerramento:
        _timer_encerramento.cancel()
        _timer_encerramento = None

# ══════════════════════════════════════════════════════════════
#  ROTAS
# ══════════════════════════════════════════════════════════════

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/keepalive')
def keepalive():
    global _conexoes_ativas

    def stream():
        global _conexoes_ativas
        with _lock:
            _conexoes_ativas += 1
            _cancelar_encerramento()
        try:
            yield 'data: ok\n\n'
            while True:
                time.sleep(1)
                yield ': keepalive\n\n'   # comentário SSE — sem evento no browser
        finally:
            with _lock:
                _conexoes_ativas -= 1
                if _conexoes_ativas == 0:
                    _agendar_encerramento()

    return Response(
        stream_with_context(stream()),
        mimetype='text/event-stream',
        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'},
    )


@app.route('/api/report', methods=['POST'])
def api_report():
    try:
        arq  = request.files.get('arquivo')
        nome = request.form.get('nome_projeto', '').strip()
        if not arq or not nome:
            return jsonify({'error': 'Arquivo e nome do projeto são obrigatórios'}), 400
        conteudo, nome_arq = gerar_relatorio_web(arq.read(), nome)
        return jsonify({'success': True, 'content': conteudo, 'filename': nome_arq})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/desembolso', methods=['POST'])
def api_desembolso():
    try:
        arq   = request.files.get('arquivo')
        nome  = request.form.get('nome_projeto', '').strip()
        corte = int(request.form.get('dia_corte', 25))
        if not arq or not nome:
            return jsonify({'error': 'Arquivo e nome do projeto são obrigatórios'}), 400
        # Salva arquivo temporário e abre gráfico em janela separada via subprocess
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as f:
            arq.save(f)
            tmp = f.name
        runner = os.path.join(BASE_DIR, '_desembolso_runner.py')
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        proc = subprocess.Popen(
            [sys.executable, runner, tmp, nome, str(corte)],
            stderr=subprocess.PIPE, stdout=subprocess.PIPE, env=env
        )
        import time; time.sleep(1.5)
        if proc.poll() is not None:
            stderr = proc.stderr.read().decode('utf-8', errors='replace').strip()
            # Extrai só a mensagem da última linha (ex: "ValueError: Planilha...")
            ultima = stderr.split('\n')[-1].strip()
            msg = ultima.split(': ', 1)[1] if ': ' in ultima else ultima
            return jsonify({'error': msg}), 500
        return jsonify({'success': True, 'message': 'Gráfico aberto em nova janela!'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500



@app.route('/api/cronograma/projetos', methods=['POST'])
def api_cronograma_projetos():
    try:
        arq = request.files.get('arquivo')
        if not arq:
            return jsonify({'error': 'Arquivo é obrigatório'}), 400
        img = gerar_projetos_web(arq.read())
        return jsonify({'success': True, 'image': img})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/cronograma/equipe', methods=['POST'])
def api_cronograma_equipe():
    try:
        arq = request.files.get('arquivo')
        if not arq:
            return jsonify({'error': 'Arquivo é obrigatório'}), 400
        results = gerar_equipe_web(arq.read())
        return jsonify({'success': True, **results})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/cronograma/clientes', methods=['POST'])
def api_cronograma_clientes():
    try:
        arq = request.files.get('arquivo')
        if not arq:
            return jsonify({'error': 'Arquivo é obrigatório'}), 400
        results = gerar_equipe_web(arq.read())
        return jsonify({'success': True, **results})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ══════════════════════════════════════════════════════════════
#  INICIALIZAÇÃO
# ══════════════════════════════════════════════════════════════

if __name__ == '__main__':
    threading.Timer(1.2, lambda: webbrowser.open('http://localhost:5000')).start()
    app.run(debug=False, port=5000)

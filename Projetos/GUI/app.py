"""
Horizontes — Ferramentas
Servidor Flask local que expõe os quatro scripts como interface web.
Execute:  python app.py
Acesse:   http://localhost:5000
"""
import os, io, re, sys, json, base64, tempfile, subprocess, threading, webbrowser
from datetime import datetime
from collections import defaultdict

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')   # backend sem janela — necessário para o servidor
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import matplotlib.dates as mdates

from flask import Flask, render_template, request, jsonify, send_file

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__,
            template_folder=os.path.join(BASE_DIR, 'templates'),
            static_folder=os.path.join(BASE_DIR, 'static'))
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50 MB

# ══════════════════════════════════════════════════════════════
#  UTILS
# ══════════════════════════════════════════════════════════════

MESES_PT_EN = {
    'janeiro': 'January', 'fevereiro': 'February', 'março': 'March',
    'abril': 'April', 'maio': 'May', 'junho': 'June', 'julho': 'July',
    'agosto': 'August', 'setembro': 'September', 'outubro': 'October',
    'novembro': 'November', 'dezembro': 'December'
}

def fig_to_b64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode('utf-8')

# ══════════════════════════════════════════════════════════════
#  REPORT SEMANAL
# ══════════════════════════════════════════════════════════════

def _formatar_datas_report(col):
    def tr(t):
        if pd.isna(t): return t
        s = str(t).lower()
        for pt, en in MESES_PT_EN.items():
            s = s.replace(pt, en)
        return s
    try:
        return pd.to_datetime(col.apply(tr), format='%d %B %Y %H:%M', errors='coerce').dt.strftime('%d/%m/%y')
    except Exception:
        return col

def _dias(d1, d2):
    if pd.isna(d1) or pd.isna(d2): return 0
    try: return (d1 - d2).days
    except: return 0

def _hierarquia(df, idx):
    pai = avo = bisavo = ''
    for i in range(idx - 1, -1, -1):
        if i < 0 or i >= len(df): continue
        try:
            nv = df.at[i, 'Nível_da_estrutura_de_tópicos']
            nm = str(df.at[i, 'Nome'])
            if nv == 3 and not pai:    pai    = nm
            elif nv == 2 and not avo:  avo    = nm
            elif nv == 1 and not bisavo: bisavo = nm
            if pai and avo and bisavo: break
        except (KeyError, IndexError): continue
    return bisavo, avo, pai

def _filtrar_recurso(df, termo):
    try:
        f1 = df['Nomes_dos_Recursos'].astype(str).str.contains(termo, case=False, na=False)
        f2 = (df['Porcentagem_Concluída'] > 0) & (df['Porcentagem_Concluída'] < 1)
        return df[f1 & f2]
    except KeyError:
        return pd.DataFrame()

def _secao_md(titulo, tarefas, df_orig, hoje, tipo):
    md = f'\n{titulo}\n'
    if tarefas.empty:
        return md + '- Não existem tarefas que cumpram os critérios desta seção\n'
    grupos = {}
    for idx, row in tarefas.iterrows():
        bisavo, avo, pai = _hierarquia(df_orig, idx)
        chave = bisavo or 'Sem categoria'
        if tipo == 'emissoes':
            linha = f'{avo} - {pai} - {row["Nome"]}: Programado para {row.get("Término","N/A")}'
        else:
            dias = '?'
            if pd.notna(row.get('Início_DT')):
                try: dias = (hoje - row['Início_DT']).days
                except: pass
            linha = f'{avo} - {pai} - {row["Nome"]}: A cargo do cliente desde {row.get("Início","N/A")} ({dias} dias)'
        grupos.setdefault(chave, []).append(linha)
    for bv, ts in grupos.items():
        if bv: md += f'\n{bv}:\n'
        for t in ts: md += f'- {t}\n'
    return md

def gerar_report(arq_bytes, nome):
    df = pd.read_excel(io.BytesIO(arq_bytes))
    if df.empty: raise ValueError('Arquivo Excel vazio')
    for col in ['Nível_da_estrutura_de_tópicos', 'Nome', 'Nomes_dos_Recursos', 'Porcentagem_Concluída']:
        if col not in df.columns:
            df[col] = 0 if 'Porcentagem' in col else ''
    for col in ['Início', 'Término', 'Início_da_Linha_de_Base', 'Término_da_linha_de_base']:
        if col in df.columns:
            df[col] = _formatar_datas_report(df[col])
            df[col + '_DT'] = pd.to_datetime(df[col], format='%d/%m/%y', errors='coerce')
    hoje = datetime.now()
    n0_rows = df[df['Nível_da_estrutura_de_tópicos'] == 0]
    n0 = n0_rows.iloc[0] if not n0_rows.empty else df.iloc[0]
    AA = n0.get('Término', 'N/A')
    BB = _dias(n0.get('Término_DT'), n0.get('Término_da_linha_de_base_DT'))
    CC = n0.get('Término_da_linha_de_base', 'N/A')
    DD = _dias(n0.get('Término_da_linha_de_base_DT'), n0.get('Início_da_Linha_de_Base_DT'))
    EE = _dias(n0.get('Término_DT'), n0.get('Início_DT'))
    conteudo = ''.join([
        f'REPORT SEMANAL {nome.upper()} — {hoje.strftime("%d/%m/%y")}\n\n',
        '📌 RESUMO:\n',
        f'- Previsão de Conclusão: {AA}, com desvio de {BB} dias corridos em relação à Linha de Base ({CC}).\n',
        f'- Duração atual estimada: {EE+1} dias corridos (Linha de Base = {DD} dias corridos).\n',
        _secao_md('📅 PRÓXIMAS EMISSÕES DE PROJETO:', _filtrar_recurso(df, 'Horizontes'), df, hoje, 'emissoes'),
        _secao_md('🔎 TAREFAS A CARGO DO CLIENTE:', _filtrar_recurso(df, 'Cliente'), df, hoje, 'analise'),
    ])
    return conteudo, f'Relatório Semanal — {nome}.md'

# ══════════════════════════════════════════════════════════════
#  CURVA DE DESEMBOLSO  (abre janela matplotlib via subprocess)
# ══════════════════════════════════════════════════════════════

def gerar_desembolso(arq_bytes, nome, dia_corte):
    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as f:
        f.write(arq_bytes)
        tmp = f.name
    runner = os.path.join(BASE_DIR, '_desembolso_runner.py')
    subprocess.Popen([sys.executable, runner, tmp, nome, str(dia_corte)])

# ══════════════════════════════════════════════════════════════
#  FÍSICO FINANCEIRO
# ══════════════════════════════════════════════════════════════

def _parse_data_pt(s):
    m = {'janeiro':1,'fevereiro':2,'março':3,'abril':4,'maio':5,'junho':6,
         'julho':7,'agosto':8,'setembro':9,'outubro':10,'novembro':11,'dezembro':12}
    try:
        p = str(s).split()
        return datetime(int(p[2]), m[p[1].lower()], int(p[0]))
    except: return None

def _competencia(data, corte):
    if not data: return None
    if data.day < corte: return data
    if data.month == 12: return datetime(data.year + 1, 1, 1)
    return datetime(data.year, data.month + 1, 1)

def gerar_fisico_financeiro(arq_bytes, nome, dia_corte):
    df = pd.read_excel(io.BytesIO(arq_bytes))
    df = df[df['Nível_da_estrutura_de_tópicos'] == 4].copy()
    df['Custo'] = df['Custo'].fillna(0)
    df['Data'] = df['Término'].apply(_parse_data_pt)
    df = df[df['Data'].notna()]
    df['Competencia'] = df['Data'].apply(lambda x: _competencia(x, dia_corte))
    df['Mes_Ano'] = df['Competencia'].apply(lambda x: x.strftime('%m/%Y') if x else None)
    df['COD_2'] = df['COD_TAREFA_AUX'].astype(str).str[:2]
    tabela = df.pivot_table(index='COD_2', columns='Mes_Ano', values='Custo', aggfunc='sum', fill_value=0)
    tabela.index.name = 'Código'
    tabela = tabela[sorted(tabela.columns, key=lambda x: datetime.strptime(x, '%m/%Y'))]
    out = io.BytesIO()
    tabela.to_excel(out)
    out.seek(0)
    return out, f'Relatório Físico Financeiro — {nome}.xlsx'

# ══════════════════════════════════════════════════════════════
#  CRONOGRAMA DE EQUIPE
# ══════════════════════════════════════════════════════════════

_CORES_CLIENTES    = ['#1f77b4','#ff7f0e','#2ca02c','#d62728','#9467bd','#daa520',
                      '#e377c2','#7f7f7f','#bcbd22','#17becf','#aec7e8','#ffbb78',
                      '#98df8a','#ff9896','#c5b0d5','#c49c94','#8c564b','#f7b6d2',
                      '#c7c7c7','#dbdb8d','#9edae5','#ff6347','#4682b4','#32cd32']
_CORES_HORIZONTES  = ['#1f77b4','#ff7f0e','#2ca02c','#d62728','#9467bd','#daa520',
                      '#e377c2','#7f7f7f','#bcbd22','#17becf','#aec7e8','#ffbb78',
                      '#98df8a','#ff9896','#c5b0d5','#c49c94']
_CORES_FORNECEDORES= ['#17becf','#bcbd22','#e377c2','#7f7f7f','#aec7e8','#f7b6d2',
                      '#8c564b','#9467bd','#ff7f0e','#1f77b4','#ffbb78','#98df8a',
                      '#ff9896','#c5b0d5','#c49c94','#2ca02c']
_CORES_ESP         = {'Sudecap': '#FFB366'}

def _mapa_cores(arq_json, paleta, itens, especiais=None):
    path = os.path.join(BASE_DIR, arq_json)
    mapa = json.load(open(path, encoding='utf-8')) if os.path.exists(path) else {}
    if especiais:
        for i in itens:
            if i in especiais: mapa[i] = especiais[i]
    disp = [c for c in paleta if c not in mapa.values()]
    for i in itens:
        if i not in mapa:
            mapa[i] = disp.pop(0) if disp else paleta[len(mapa) % len(paleta)]
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(mapa, f, indent=4, ensure_ascii=False)
    return mapa

def _carregar_cronograma(arq_bytes):
    df = pd.read_excel(io.BytesIO(arq_bytes), sheet_name='Tabela_Tarefas1')
    df = df.rename(columns={'Nome_da_Tarefa': 'Nome'})
    df = df[df['Ativo'] == 'Sim'].copy()
    meses_cap = {k.capitalize(): v for k, v in MESES_PT_EN.items()}
    def tr(s):
        if pd.isna(s): return s
        for pt, en in meses_cap.items():
            s = re.sub(pt, en, str(s))
        return s
    df['Início_dt']  = pd.to_datetime(df['Início'].apply(tr),  errors='coerce', format='%d %B %Y %H:%M')
    df['Término_dt'] = pd.to_datetime(df['Término'].apply(tr), errors='coerce', format='%d %B %Y %H:%M')
    return df

def gerar_cronograma_projetos(arq_bytes):
    df = _carregar_cronograma(arq_bytes)
    clientes = defaultdict(list)
    cliente_atual = None
    for _, row in df.iterrows():
        nv = row['Nível_da_estrutura_de_tópicos']
        if nv == 1:
            cliente_atual = row['Nome']
        elif nv == 2 and cliente_atual and pd.notna(row['Início_dt']) and pd.notna(row['Término_dt']):
            clientes[cliente_atual].append({'Nome': row['Nome'], 'Início': row['Início_dt'], 'Término': row['Término_dt']})
    projs, lg = [], 0
    for cli in sorted(clientes):
        ps = sorted(clientes[cli], key=lambda x: x['Início'])
        linhas = []
        for p in ps:
            ini, fim = p['Início'], p['Término']
            lr = next((i for i, u in enumerate(linhas) if ini >= u), None)
            if lr is None: linhas.append(fim); lr = len(linhas) - 1
            else: linhas[lr] = fim
            projs.append({'Cliente': cli, 'Projeto': p['Nome'], 'Início': ini, 'Término': fim, 'Y': lg + lr})
        lg += len(linhas) + 1
    df_p = pd.DataFrame(projs)
    if df_p.empty: raise ValueError('Nenhum projeto com datas válidas')
    cores = _mapa_cores('cores_clientes.json', _CORES_CLIENTES, sorted(df_p['Cliente'].unique()), _CORES_ESP)
    hoje  = datetime.now()
    fig, ax = plt.subplots(figsize=(16, 12))
    for _, r in df_p.iterrows():
        dur = r['Término'] - r['Início']
        ax.barh(y=r['Y'], width=dur, left=r['Início'], height=0.85, align='center',
                color=cores[r['Cliente']], edgecolor='white', linewidth=0.5)
        ax.text(r['Início'] + dur / 50, r['Y'], r['Projeto'], va='center', ha='left', fontsize=8)
    ax.axvline(x=hoje, color='red', linestyle='--', linewidth=1.5, alpha=0.7)
    y_labels, y_ticks, y_colors = [], [], []
    for c in sorted(df_p['Cliente'].unique()):
        sub = df_p[df_p['Cliente'] == c]
        y_labels.append(c); y_ticks.append((sub['Y'].min()+sub['Y'].max())/2); y_colors.append(cores[c])
    ax.set_yticks(y_ticks); ax.set_yticklabels(y_labels, fontsize=10, fontweight='bold')
    for tl, col in zip(ax.get_yticklabels(), y_colors): tl.set_color(col)
    ax.set_xlim(df_p['Início'].min().replace(day=1), df_p['Término'].max().replace(day=1) + pd.offsets.MonthEnd(1))
    ax.xaxis.set_major_locator(mdates.MonthLocator()); ax.xaxis.set_major_formatter(mdates.DateFormatter('%b/%y'))
    ax.tick_params(axis='x', rotation=0, labelsize=9, colors='gray')
    ax.grid(axis='x', linestyle='--', color='lightgray', linewidth=0.7)
    ax.set_title('Cronograma de Projetos por Cliente', fontsize=18, fontweight='bold', pad=20)
    ax.set_xlabel('Data', fontsize=12, fontweight='bold'); ax.set_ylabel('Clientes', fontsize=12, fontweight='bold')
    plt.tight_layout()
    return fig_to_b64(fig)

def gerar_cronograma_equipe(arq_bytes):
    df = _carregar_cronograma(arq_bytes)
    hoje = datetime.now()
    results = {}
    configs = [
        ('Horizontes',   'cores_horizontes.json',   _CORES_HORIZONTES,   'Relatório de Alocação de Equipe'),
        ('Fornecedores', 'cores_fornecedores.json',  _CORES_FORNECEDORES, 'Relatório de Alocação de Fornecedores'),
    ]
    for grupo, arq_json, paleta, titulo in configs:
        df_g = df[df['Grupo_de_recursos'] == grupo].copy()
        if df_g.empty: continue
        df_g = df_g.assign(Nomes_dos_recursos=df_g['Nomes_dos_recursos'].str.split(';')).explode('Nomes_dos_recursos')
        df_g['Nomes_dos_recursos'] = df_g['Nomes_dos_recursos'].str.strip()
        df_g = df_g[df_g['Término_dt'] >= hoje].copy()
        if df_g.empty: continue
        por_recurso = defaultdict(list)
        for _, row in df_g.iterrows(): por_recurso[row['Nomes_dos_recursos']].append(row)
        alocs = []
        for rec, tarefas in por_recurso.items():
            tarefas = sorted(tarefas, key=lambda x: x['Início_dt'])
            linhas = []
            for t in tarefas:
                ini, fim = t['Início_dt'], t['Término_dt']
                for i, u in enumerate(linhas):
                    if ini > u: linhas[i] = fim; linha = i; break
                else: linhas.append(fim); linha = len(linhas) - 1
                alocs.append({'Recurso': rec, 'Nome': t['Nome'], 'Início': ini, 'Fim': fim, 'Linha': linha})
        df_a = pd.DataFrame(alocs); df_a['Y'] = np.nan
        recursos = sorted(df_a['Recurso'].unique())
        y = 0
        for r in recursos:
            for idx, _ in df_a[df_a['Recurso'] == r].sort_values(['Linha', 'Início']).iterrows():
                df_a.loc[idx, 'Y'] = y; y += 1
        cores = _mapa_cores(arq_json, paleta, recursos)
        fig, ax = plt.subplots(figsize=(14, 10))
        for _, r in df_a.iterrows():
            dur = r['Fim'] - r['Início']
            ax.barh(y=r['Y'], width=dur, left=r['Início'], height=0.7, align='center', color=cores[r['Recurso']])
            ax.text(r['Início'] + dur/50, r['Y'], r['Nome'], va='center', ha='left', fontsize=9)
        ax.axvline(x=hoje, color='red', linestyle='--', linewidth=1)
        y_labels, y_ticks, y_colors = [], [], []
        for rec in recursos:
            pos = df_a[df_a['Recurso'] == rec]['Y'].values
            y_labels.append(rec); y_ticks.append((pos.min()+pos.max())/2); y_colors.append(cores[rec])
        ax.set_yticks(y_ticks); ax.set_yticklabels(y_labels, fontsize=10, fontweight='bold')
        for tl, col in zip(ax.get_yticklabels(), y_colors): tl.set_color(col)
        ax.set_xlim(df_a['Início'].min().replace(day=1), df_a['Fim'].max().replace(day=1) + pd.offsets.MonthEnd(1))
        ax.xaxis.set_major_locator(mdates.MonthLocator()); ax.xaxis.set_major_formatter(mdates.DateFormatter('%b/%y'))
        ax.tick_params(axis='x', rotation=0, labelsize=10, colors='gray')
        ax.grid(axis='x', linestyle='--', color='lightgray', linewidth=0.8)
        ax.set_title(titulo, fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel('Data', fontsize=11, fontweight='bold'); ax.set_ylabel('Recursos', fontsize=11, fontweight='bold')
        plt.tight_layout()
        results[grupo.lower()] = fig_to_b64(fig)
    return results

# ══════════════════════════════════════════════════════════════
#  ROTAS FLASK
# ══════════════════════════════════════════════════════════════

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/report', methods=['POST'])
def api_report():
    try:
        arq  = request.files.get('arquivo')
        nome = request.form.get('nome_projeto', '').strip()
        if not arq or not nome:
            return jsonify({'error': 'Arquivo e nome do projeto são obrigatórios'}), 400
        conteudo, nome_arq = gerar_report(arq.read(), nome)
        buf = io.BytesIO(conteudo.encode('utf-8'))
        return send_file(buf, as_attachment=True, download_name=nome_arq, mimetype='text/markdown')
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
        gerar_desembolso(arq.read(), nome, corte)
        return jsonify({'success': True, 'message': 'Gráfico aberto em nova janela!'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/fisico-financeiro', methods=['POST'])
def api_fisico():
    try:
        arq   = request.files.get('arquivo')
        nome  = request.form.get('nome_projeto', '').strip()
        corte = int(request.form.get('dia_corte', 25))
        if not arq or not nome:
            return jsonify({'error': 'Arquivo e nome do projeto são obrigatórios'}), 400
        output, nome_arq = gerar_fisico_financeiro(arq.read(), nome, corte)
        return send_file(output, as_attachment=True, download_name=nome_arq,
                         mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/cronograma/projetos', methods=['POST'])
def api_cronograma_projetos():
    try:
        arq = request.files.get('arquivo')
        if not arq:
            return jsonify({'error': 'Arquivo é obrigatório'}), 400
        img = gerar_cronograma_projetos(arq.read())
        return jsonify({'success': True, 'image': img})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/cronograma/equipe', methods=['POST'])
def api_cronograma_equipe():
    try:
        arq = request.files.get('arquivo')
        if not arq:
            return jsonify({'error': 'Arquivo é obrigatório'}), 400
        results = gerar_cronograma_equipe(arq.read())
        return jsonify({'success': True, **results})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ══════════════════════════════════════════════════════════════
#  INICIALIZAÇÃO
# ══════════════════════════════════════════════════════════════

if __name__ == '__main__':
    threading.Timer(1.2, lambda: webbrowser.open('http://localhost:5000')).start()
    app.run(debug=False, port=5000)

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from collections import defaultdict
import numpy as np
from datetime import datetime
import re
import os
import json

# ============================
# CONFIGURAÇÕES PADRÃO DO MOTOR
# ============================

# Tradução dos meses
meses_pt_en = {
    'Janeiro': 'January', 'Fevereiro': 'February', 'Março': 'March', 'Abril': 'April',
    'Maio': 'May', 'Junho': 'June', 'Julho': 'July', 'Agosto': 'August',
    'Setembro': 'September', 'Outubro': 'October', 'Novembro': 'November', 'Dezembro': 'December'
}

# Paleta de bordas por recurso (cores vivas e distintas)
PALETA = [
    '#E63946', '#2196F3', '#4CAF50', '#FF9800',
    '#9C27B0', '#00BCD4', '#F06292', '#8BC34A',
    '#FF5722', '#3F51B5', '#009688', '#FFC107',
    '#E91E63', '#03A9F4', '#CDDC39', '#795548',
    '#673AB7', '#76FF03', '#FF1744', '#00E5FF',
]

# Cor de preenchimento uniforme das barras
COR_BARRA = '#D0D0D0'

cores_horizontes_base   = PALETA
cores_fornecedores_base = PALETA

# Arquivos de mapeamento persistente
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ARQ_CORES_HORIZONTES   = os.path.join(_SCRIPT_DIR, 'cores_horizontes.json')
ARQ_CORES_FORNECEDORES = os.path.join(_SCRIPT_DIR, 'cores_fornecedores.json')
ARQ_GRUPOS_RECURSOS    = os.path.join(_SCRIPT_DIR, 'grupos_recursos.json')

# Tamanho da figura
FIGSIZE = (14, 10)

# ============================
# FUNÇÕES AUXILIARES
# ============================

def traduzir_meses(data_str):
    if pd.isna(data_str):
        return data_str
    for pt, en in meses_pt_en.items():
        data_str = re.sub(pt, en, data_str)
    return data_str

def carregar_dados(nome_arquivo):
    try:
        df = pd.read_excel(nome_arquivo, sheet_name='Tabela_Tarefas1')
    except Exception:
        raise ValueError("Planilha incompatível. Aba 'Tabela_Tarefas1' não encontrada no arquivo.")

    colunas_necessarias = ['Início', 'Término', 'Ativo', 'Grupo_de_recursos', 'Nomes_dos_recursos']
    faltando = [c for c in colunas_necessarias if c not in df.columns]
    # Coluna de tarefa pode ter nomes alternativos
    _nomes_tarefa = ['Nome_da_Tarefa', 'Nome', 'Task', 'Name']
    col_tarefa = next((c for c in _nomes_tarefa if c in df.columns), None)
    if col_tarefa is None:
        faltando.append('Nome_da_Tarefa / Nome / Task / Name')
    if faltando:
        raise ValueError(f"Planilha incompatível. Colunas ausentes: {', '.join(faltando)}")

    df['Início_en'] = df['Início'].apply(traduzir_meses)
    df['Término_en'] = df['Término'].apply(traduzir_meses)
    df['Início_dt'] = pd.to_datetime(df['Início_en'], errors='coerce', format='%d %B %Y %H:%M')
    df['Término_dt'] = pd.to_datetime(df['Término_en'], errors='coerce', format='%d %B %Y %H:%M')
    # Normalizar nome da coluna de tarefa
    if col_tarefa != 'Nome':
        df = df.rename(columns={col_tarefa: 'Nome'})
    df = df[df['Ativo'] == 'Sim']
    return df

def _carregar_mapa_grupos():
    if os.path.exists(ARQ_GRUPOS_RECURSOS):
        with open(ARQ_GRUPOS_RECURSOS, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def _salvar_mapa_grupos(mapa):
    with open(ARQ_GRUPOS_RECURSOS, 'w', encoding='utf-8') as f:
        json.dump(mapa, f, indent=4, ensure_ascii=False, sort_keys=True)

def resolver_grupos(df, modo_web=False):
    """Carrega o mapa recurso→grupo e resolve desconhecidos (prompt no CLI, erro na web)."""
    mapa = _carregar_mapa_grupos()

    todos = set()
    for val in df['Nomes_dos_recursos'].dropna():
        for r in str(val).split(';'):
            r = r.strip()
            if r:
                todos.add(r)

    desconhecidos = sorted(todos - set(mapa.keys()))

    if desconhecidos:
        if modo_web:
            raise ValueError(
                f"Recursos sem grupo definido: {', '.join(desconhecidos)}. "
                f"Adicione-os ao arquivo grupos_recursos.json."
            )
        for r in desconhecidos:
            while True:
                resp = input(f"Grupo de '{r}'? [H]orizontes / [F]ornecedores: ").strip().upper()
                if resp in ('H', 'HORIZONTES'):
                    mapa[r] = 'Horizontes'
                    break
                elif resp in ('F', 'FORNECEDORES'):
                    mapa[r] = 'Fornecedores'
                    break
                print("  Digite H ou F.")
        _salvar_mapa_grupos(mapa)

    return mapa

def preparar_grupo(df, grupo, mapa_grupos):
    """Filtra e explode recursos cujo grupo (do mapa) corresponde ao grupo solicitado."""
    df2 = df.copy()
    df2 = df2.assign(Nomes_dos_recursos=df2['Nomes_dos_recursos'].str.split(';'))
    df2 = df2.explode('Nomes_dos_recursos')
    df2['Nomes_dos_recursos'] = df2['Nomes_dos_recursos'].str.strip()
    df2 = df2[df2['Nomes_dos_recursos'].map(lambda r: mapa_grupos.get(r) == grupo)].copy()
    return df2

def empilhar_tarefas(df_grupo):
    # Filtrar tarefas com data de término anterior à data atual
    hoje = datetime.now()
    df_grupo = df_grupo[df_grupo['Término_dt'] >= hoje].copy()
    
    # Se não houver tarefas após o filtro, retornar DataFrames vazios
    if df_grupo.empty:
        return pd.DataFrame(), []
    
    tarefa_por_recurso = defaultdict(list)
    for _, row in df_grupo.iterrows():
        recurso = row['Nomes_dos_recursos']
        tarefa_por_recurso[recurso].append(row)

    alocacoes = []
    for recurso, tarefas in tarefa_por_recurso.items():
        tarefas = sorted(tarefas, key=lambda x: x['Início_dt'])
        linhas_ocupadas = []
        for tarefa in tarefas:
            inicio = tarefa['Início_dt']
            fim = tarefa['Término_dt']
            for i, ultima_data in enumerate(linhas_ocupadas):
                if inicio > ultima_data:
                    linhas_ocupadas[i] = fim
                    linha = i
                    break
            else:
                linhas_ocupadas.append(fim)
                linha = len(linhas_ocupadas) - 1
            alocacoes.append({
                'Recurso': recurso, 'Nome': tarefa['Nome'], 'Início': inicio, 'Fim': fim, 'Linha': linha
            })

    df_aloc = pd.DataFrame(alocacoes)
    df_aloc['Y_absoluto'] = np.nan
    recursos = sorted(df_aloc['Recurso'].unique())
    linha_global = 0
    for recurso in recursos:
        linhas_recurso = df_aloc[df_aloc['Recurso'] == recurso].sort_values(by=['Linha', 'Início'])
        for idx, row in linhas_recurso.iterrows():
            df_aloc.loc[idx, 'Y_absoluto'] = linha_global
            linha_global += 1
    return df_aloc, recursos

def carregar_mapa_cores(arq_json, paleta_base, recursos):
    if os.path.exists(arq_json):
        with open(arq_json, 'r', encoding='utf-8') as f:
            mapa = json.load(f)
    else:
        mapa = {}

    # Remove recursos ausentes no Excel atual e mantém apenas os presentes
    mapa = {r: c for r, c in mapa.items() if r in recursos}

    cores_disponiveis = [c for c in paleta_base if c not in mapa.values()]

    for recurso in recursos:
        if recurso not in mapa:
            if cores_disponiveis:
                mapa[recurso] = cores_disponiveis.pop(0)
            else:
                # Se esgotar a paleta, continua reaproveitando de forma circular
                mapa[recurso] = paleta_base[len(mapa) % len(paleta_base)]

    with open(arq_json, 'w', encoding='utf-8') as f:
        json.dump(mapa, f, indent=4, ensure_ascii=False)

    return mapa

def plotar(df_aloc, recursos, cores_dict, titulo, arquivo_saida):
    if df_aloc.empty:
        print(f'Nenhuma tarefa ativa encontrada para {titulo}')
        return

    BAR_HEIGHT = 0.82
    hoje = datetime.now()
    data_inicio_min = df_aloc['Início'].min().replace(day=1)
    data_fim_max    = df_aloc['Fim'].max().replace(day=1) + pd.offsets.MonthEnd(1)
    borda_largura   = (data_fim_max - data_inicio_min).days * 0.008

    fig, ax = plt.subplots(figsize=FIGSIZE)

    textos = []
    for _, row in df_aloc.iterrows():
        inicio, fim = row['Início'], row['Fim']
        duracao, y_pos = fim - inicio, row['Y_absoluto']
        borda = cores_dict[row['Recurso']]

        ax.barh(y=y_pos, width=duracao, left=inicio, height=BAR_HEIGHT,
                color=COR_BARRA, edgecolor='white', linewidth=0.5, zorder=2)
        ax.barh(y=y_pos, width=borda_largura, left=inicio, height=BAR_HEIGHT,
                color=borda, edgecolor='none', zorder=3)
        txt_x = inicio + pd.Timedelta(days=borda_largura * 1.2) + duracao / 50
        t = ax.text(txt_x, y_pos, row['Nome'],
                    va='center', ha='left', fontsize=7.5, color='#333', zorder=4)
        textos.append(t)

    y_max = df_aloc['Y_absoluto'].max()
    y_min = df_aloc['Y_absoluto'].min()
    ax.axvline(x=hoje, color='red', linestyle='--', linewidth=1, zorder=5)
    ax.text(hoje, y_max + 0.55, 'Hoje', color='red', va='bottom', ha='center', fontsize=10)

    y_labels, y_ticks, y_colors = [], [], []
    for recurso in recursos:
        posicoes = df_aloc[df_aloc['Recurso'] == recurso]['Y_absoluto'].values
        y_labels.append(recurso)
        y_ticks.append((posicoes.min() + posicoes.max()) / 2)
        y_colors.append(cores_dict[recurso])

    ax.set_yticks(y_ticks)
    ax.set_yticklabels(y_labels, fontsize=10, fontweight='bold')
    for ticklabel, color in zip(ax.get_yticklabels(), y_colors):
        ticklabel.set_color(color)

    ax.set_ylim(y_min - 0.6, y_max + 0.6)
    ax.set_xlim(data_inicio_min, data_fim_max)
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b/%y'))
    ax.tick_params(axis='x', colors='gray')
    ax.grid(axis='x', linestyle='--', color='#CCCCCC', linewidth=0.7, zorder=1)
    ax.set_title(titulo, fontsize=16, fontweight='bold', pad=20)
    ax.set_xlabel('Data', fontsize=11, fontweight='bold')
    ax.set_ylabel('Recursos', fontsize=11, fontweight='bold')
    plt.tight_layout()

    # Ajustar fonte para caber na altura da barra
    fig.canvas.draw()
    trans = ax.transData
    bar_h_px = abs(trans.transform((0, BAR_HEIGHT))[1] - trans.transform((0, 0))[1])
    bar_h_pt = bar_h_px / fig.dpi * 72 * 0.72
    for t in textos:
        t.set_fontsize(min(9, bar_h_pt))

    plt.savefig(arquivo_saida, dpi=300, bbox_inches='tight')
    plt.close()

# ============================
# EXECUÇÃO DO MOTOR
# ============================

def verificar_recursos_desconhecidos(arquivo_bytes):
    """Retorna lista de recursos no arquivo que não estão em grupos_recursos.json."""
    import tempfile as _tmp
    with _tmp.NamedTemporaryFile(delete=False, suffix='.xlsx') as f:
        f.write(arquivo_bytes)
        tmp = f.name
    try:
        df = carregar_dados(tmp)
        mapa = _carregar_mapa_grupos()
        todos = set()
        for val in df['Nomes_dos_recursos'].dropna():
            for r in str(val).split(';'):
                r = r.strip()
                if r:
                    todos.add(r)
        return sorted(todos - set(mapa.keys()))
    finally:
        os.unlink(tmp)

def _iso_dt(valor):
    """Converte data ISO 'YYYY-MM-DD' (formato do JSON do PWA) em Timestamp (ou NaT)."""
    if not valor:
        return pd.NaT
    return pd.to_datetime(str(valor)[:10], format='%Y-%m-%d', errors='coerce')


def _gerar_grupos(df, grupos_novos=None):
    """Núcleo compartilhado: recebe um DataFrame já com as colunas
    'Nome', 'Nomes_dos_recursos' (separados por ';'), 'Início_dt' e 'Término_dt',
    e devolve dict com PNGs base64 (chaves 'horizontes' e 'fornecedores').
    Usado tanto pelo fluxo de Excel quanto pelo fluxo que lê o JSON do PWA."""
    import io as _io, base64 as _b64

    if grupos_novos:
        mapa = _carregar_mapa_grupos()
        mapa.update(grupos_novos)
        _salvar_mapa_grupos(mapa)
    mapa_grupos = resolver_grupos(df, modo_web=True)
    results = {}
    for grupo, arq_json, paleta, titulo, key in [
        ('Horizontes',   ARQ_CORES_HORIZONTES,   cores_horizontes_base,   'Cronograma de Projetos Por Equipe Interna',  'horizontes'),
        ('Fornecedores', ARQ_CORES_FORNECEDORES,  cores_fornecedores_base, 'Cronograma de Projetos por Fornecedores',   'fornecedores'),
    ]:
        df_grupo = preparar_grupo(df, grupo, mapa_grupos)
        df_aloc, recursos = empilhar_tarefas(df_grupo)
        if not df_aloc.empty:
            cores_dict = carregar_mapa_cores(arq_json, paleta, recursos)
            buf = _io.BytesIO()
            plotar(df_aloc, recursos, cores_dict, titulo, buf)
            buf.seek(0)
            results[key] = _b64.b64encode(buf.read()).decode('utf-8')
    return results


def _df_de_tarefas_json(tarefas):
    """Monta o DataFrame que o motor espera a partir da lista de tarefas do JSON
    do PWA (mesmas tarefas usadas pelos dashboards). O JSON junta os recursos por
    ', '; o motor espera ';'. Mantém só tarefas que têm pelo menos um recurso."""
    linhas = []
    for t in tarefas:
        recursos = ';'.join(r.strip() for r in str(t.get('resources') or '').split(',') if r.strip())
        if not recursos:
            continue
        linhas.append({
            'Nome': t.get('name', ''),
            'Nomes_dos_recursos': recursos,
            'Início_dt': _iso_dt(t.get('start')),
            'Término_dt': _iso_dt(t.get('end')),
        })
    return pd.DataFrame(linhas)


def verificar_recursos_desconhecidos_json(tarefas):
    """Versão JSON: retorna recursos das tarefas que ainda não têm grupo em grupos_recursos.json."""
    mapa = _carregar_mapa_grupos()
    todos = set()
    for t in tarefas:
        for r in str(t.get('resources') or '').split(','):
            r = r.strip()
            if r:
                todos.add(r)
    return sorted(todos - set(mapa.keys()))


def gerar_para_web_json(tarefas, grupos_novos=None):
    """Gera os cronogramas de alocação (Equipe Interna / Fornecedores) direto do
    JSON do PWA, sem Excel. Retorna dict com PNGs base64 — saída idêntica à versão
    de Excel, pois reaproveita o mesmo núcleo `_gerar_grupos`."""
    df = _df_de_tarefas_json(tarefas)
    if df.empty:
        return {}
    return _gerar_grupos(df, grupos_novos)


def gerar_para_web(arquivo_bytes, grupos_novos=None):
    """Para uso no portal web. Retorna dict com imagens PNG como base64 (chaves: 'horizontes', 'fornecedores').
    grupos_novos: dict {recurso: grupo} com atribuições informadas pelo usuário na UI."""
    import tempfile as _tmp

    with _tmp.NamedTemporaryFile(delete=False, suffix='.xlsx') as f:
        f.write(arquivo_bytes)
        tmp = f.name
    try:
        df = carregar_dados(tmp)
        return _gerar_grupos(df, grupos_novos)
    finally:
        os.unlink(tmp)


if __name__ == "__main__":

    arquivos_xlsx = [f for f in os.listdir('.') if f.endswith('.xlsx')]
    if not arquivos_xlsx:
        print('Nenhum arquivo .xlsx encontrado na pasta.')
        exit()

    print('Arquivos encontrados:')
    for i, nome_arq in enumerate(arquivos_xlsx, 1):
        print(f'{i} - {nome_arq}')

    escolha = int(input('Digite o número do arquivo desejado: '))
    arquivo = arquivos_xlsx[escolha-1]

    df = carregar_dados(arquivo)
    mapa_grupos = resolver_grupos(df, modo_web=False)

    # --- Horizontes ---
    df_h = preparar_grupo(df, 'Horizontes', mapa_grupos)
    df_aloc_h, recursos_h = empilhar_tarefas(df_h)
    if not df_aloc_h.empty:
        cores_dict_h = carregar_mapa_cores(ARQ_CORES_HORIZONTES, cores_horizontes_base, recursos_h)
        plotar(df_aloc_h, recursos_h, cores_dict_h, 'Cronograma de Projetos Por Equipe Interna', 'horizontes.png')

    # --- Fornecedores ---
    df_f = preparar_grupo(df, 'Fornecedores', mapa_grupos)
    df_aloc_f, recursos_f = empilhar_tarefas(df_f)
    if not df_aloc_f.empty:
        cores_dict_f = carregar_mapa_cores(ARQ_CORES_FORNECEDORES, cores_fornecedores_base, recursos_f)
        plotar(df_aloc_f, recursos_f, cores_dict_f, 'Cronograma de Projetos por Fornecedores', 'fornecedores.png')

    print('Gráficos gerados com sucesso!')
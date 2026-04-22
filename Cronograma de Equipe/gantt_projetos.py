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
# CONFIGURAÇÕES PADRÃO
# ============================

# Tradução dos meses
meses_pt_en = {
    'Janeiro': 'January', 'Fevereiro': 'February', 'Março': 'March', 'Abril': 'April',
    'Maio': 'May', 'Junho': 'June', 'Julho': 'July', 'Agosto': 'August',
    'Setembro': 'September', 'Outubro': 'October', 'Novembro': 'November', 'Dezembro': 'December'
}

# Paleta de cores expandida (24 cores — compartilhada com gantt_clientes)
cores_clientes_base = [
    '#F26868', '#96ECAF', '#D5B7EA', '#F2E168',
    '#96DEEC', '#EAB7D3', '#8AF268', '#9A96EC',
    '#EAC8B7', '#EBBC3C', '#E596EC', '#DFEAB7',
    '#68ADF2', '#EC96A8', '#F159AA', '#9C68F2',
    '#ECD096', '#B7EAE8', '#F268CF', '#DE3962',
    '#D39E68', '#F5A865', '#40D6E7', '#AAB5C4',
]

# Cores específicas para clientes
CORES_ESPECIFICAS = {
    'Sudecap': '#FFB366'  # Laranja claro
}

# Arquivo de mapeamento de cores persistente
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ARQ_CORES_CLIENTES = os.path.join(_SCRIPT_DIR, 'cores_clientes.json')

# Tamanho da figura
FIGSIZE = (16, 12)

# ============================
# FUNÇÕES AUXILIARES
# ============================

def traduzir_meses(data_str):
    """Traduz nomes de meses de português para inglês"""
    if pd.isna(data_str):
        return data_str
    for pt, en in meses_pt_en.items():
        data_str = re.sub(pt, en, data_str)
    return data_str

def carregar_dados(nome_arquivo):
    """Carrega e prepara os dados do arquivo Excel"""
    try:
        df = pd.read_excel(nome_arquivo, sheet_name='Tabela_Tarefas1')
    except Exception:
        raise ValueError("Planilha incompatível. Aba 'Tabela_Tarefas1' não encontrada no arquivo.")

    colunas_necessarias = ['Início', 'Término', 'Ativo', 'Nível_da_estrutura_de_tópicos']
    faltando = [c for c in colunas_necessarias if c not in df.columns]
    # Coluna de tarefa pode ter nomes alternativos
    _nomes_tarefa = ['Nome_da_Tarefa', 'Nome', 'Task', 'Name']
    col_tarefa = next((c for c in _nomes_tarefa if c in df.columns), None)
    if col_tarefa is None:
        faltando.append('Nome_da_Tarefa / Nome / Task / Name')
    if faltando:
        raise ValueError(f"Planilha incompatível. Colunas ausentes: {', '.join(faltando)}")

    # Traduzir datas
    df['Início_en'] = df['Início'].apply(traduzir_meses)
    df['Término_en'] = df['Término'].apply(traduzir_meses)

    # Converter para datetime
    df['Início_dt'] = pd.to_datetime(df['Início_en'], errors='coerce', format='%d %B %Y %H:%M')
    df['Término_dt'] = pd.to_datetime(df['Término_en'], errors='coerce', format='%d %B %Y %H:%M')

    # Normalizar nome da coluna de tarefa
    if col_tarefa != 'Nome':
        df = df.rename(columns={col_tarefa: 'Nome'})
    
    # Filtrar apenas tarefas ativas
    df = df[df['Ativo'] == 'Sim']
    
    return df

def extrair_clientes_projetos(df):
    """
    Extrai clientes (nível 1) e projetos (nível 2) do DataFrame
    Retorna uma estrutura de dados com clientes e seus respectivos projetos
    """
    # Verificar se a coluna de nível existe
    if 'Nível_da_estrutura_de_tópicos' not in df.columns:
        print("AVISO: Coluna 'Nível_da_estrutura_de_tópicos' não encontrada!")
        print("Colunas disponíveis:", df.columns.tolist())
        return {}
    
    clientes_projetos = defaultdict(list)
    cliente_atual = None
    
    for idx, row in df.iterrows():
        nivel = row['Nível_da_estrutura_de_tópicos']
        
        # Nível 1 = Cliente
        if nivel == 1:
            cliente_atual = row['Nome']
            # Garantir que o cliente existe no dicionário
            if cliente_atual not in clientes_projetos:
                clientes_projetos[cliente_atual] = []
        
        # Nível 2 = Projeto
        elif nivel == 2 and cliente_atual is not None:
            # Verificar se tem datas válidas
            if pd.notna(row['Início_dt']) and pd.notna(row['Término_dt']):
                clientes_projetos[cliente_atual].append({
                    'Nome': row['Nome'],
                    'Início': row['Início_dt'],
                    'Término': row['Término_dt'],
                    'ID': idx
                })
    
    return dict(clientes_projetos)

def organizar_projetos_por_linha(clientes_projetos):
    """
    Organiza os projetos em linhas, evitando sobreposição dentro do mesmo cliente
    Retorna DataFrame com posição Y calculada para cada projeto
    """
    projetos_organizados = []
    linha_global = 0
    
    # Ordenar clientes alfabeticamente para consistência visual
    clientes_ordenados = sorted(clientes_projetos.keys())
    
    for cliente in clientes_ordenados:
        projetos = clientes_projetos[cliente]
        
        if not projetos:
            continue
        
        # Ordenar projetos por data de início
        projetos_ordenados = sorted(projetos, key=lambda x: x['Início'])
        
        # Algoritmo de empilhamento para evitar sobreposição
        linhas_ocupadas = []
        
        for projeto in projetos_ordenados:
            inicio = projeto['Início']
            fim = projeto['Término']
            
            # Tentar encontrar uma linha disponível
            linha_relativa = None
            for i, ultima_data in enumerate(linhas_ocupadas):
                if inicio >= ultima_data:
                    linhas_ocupadas[i] = fim
                    linha_relativa = i
                    break
            
            # Se não encontrou linha disponível, criar nova
            if linha_relativa is None:
                linhas_ocupadas.append(fim)
                linha_relativa = len(linhas_ocupadas) - 1
            
            # Adicionar projeto com sua posição
            projetos_organizados.append({
                'Cliente': cliente,
                'Projeto': projeto['Nome'],
                'Início': inicio,
                'Término': fim,
                'Linha_relativa': linha_relativa,
                'Linha_global': linha_global + linha_relativa
            })
        
        # Avançar linha global para o próximo cliente
        linha_global += len(linhas_ocupadas) + 1  # +1 para espaçamento entre clientes
    
    return pd.DataFrame(projetos_organizados)

def carregar_mapa_cores(arq_json, paleta_base, clientes):
    """Carrega ou cria mapeamento de cores para clientes"""
    if os.path.exists(arq_json):
        with open(arq_json, 'r', encoding='utf-8') as f:
            mapa = json.load(f)
    else:
        mapa = {}

    # Remove clientes ausentes no Excel atual e mantém apenas os presentes
    mapa = {c: cor for c, cor in mapa.items() if c in clientes}

    # Aplicar cores específicas primeiro
    for cliente in clientes:
        if cliente in CORES_ESPECIFICAS:
            mapa[cliente] = CORES_ESPECIFICAS[cliente]

    cores_disponiveis = [c for c in paleta_base if c not in mapa.values()]

    for cliente in clientes:
        if cliente not in mapa:
            if cores_disponiveis:
                mapa[cliente] = cores_disponiveis.pop(0)
            else:
                # Se esgotar a paleta, reutilizar de forma circular
                mapa[cliente] = paleta_base[len(mapa) % len(paleta_base)]

    with open(arq_json, 'w', encoding='utf-8') as f:
        json.dump(mapa, f, indent=4, ensure_ascii=False)
    
    return mapa

def plotar_gantt_projetos(df_projetos, cores_dict, titulo, arquivo_saida):
    """Gera o gráfico de Gantt de projetos agrupados por cliente"""
    
    if df_projetos.empty:
        print(f'Nenhum projeto encontrado para {titulo}')
        return
    
    hoje = datetime.now()
    
    # Definir limites do gráfico
    data_inicio_min = df_projetos['Início'].min().replace(day=1)
    data_fim_max = df_projetos['Término'].max().replace(day=1) + pd.offsets.MonthEnd(1)
    
    plt.figure(figsize=FIGSIZE)
    
    # Plotar cada projeto
    for _, row in df_projetos.iterrows():
        inicio = row['Início']
        fim = row['Término']
        duracao = fim - inicio
        y_pos = row['Linha_global']
        cor = cores_dict[row['Cliente']]
        
        # Barra do projeto
        plt.barh(y=y_pos, width=duracao, left=inicio, height=0.85, 
                align='center', color=cor, edgecolor='white', linewidth=0.5)
        
        # Nome do projeto
        plt.text(inicio + duracao / 50, y_pos, row['Projeto'], 
                va='center', ha='left', fontsize=8, color='black')
    
    # Linha vertical "Hoje"
    plt.axvline(x=hoje, color='red', linestyle='--', linewidth=1.5, alpha=0.7)
    plt.text(hoje, plt.ylim()[1], 'Hoje', color='red', va='bottom', 
            ha='center', fontsize=10, fontweight='bold')
    
    # Configurar labels do eixo Y (clientes)
    clientes = df_projetos['Cliente'].unique()
    y_labels = []
    y_ticks = []
    y_colors = []
    
    for cliente in sorted(clientes):
        projetos_cliente = df_projetos[df_projetos['Cliente'] == cliente]
        pos_min = projetos_cliente['Linha_global'].min()
        pos_max = projetos_cliente['Linha_global'].max()
        pos_central = (pos_min + pos_max) / 2
        
        y_labels.append(cliente)
        y_ticks.append(pos_central)
        y_colors.append(cores_dict[cliente])
    
    plt.yticks(y_ticks, y_labels, fontsize=10, fontweight='bold')
    
    # Colorir labels dos clientes
    ax = plt.gca()
    for ticklabel, color in zip(ax.get_yticklabels(), y_colors):
        ticklabel.set_color(color)
    
    # Adicionar linhas horizontais separando clientes
    for i, cliente in enumerate(sorted(clientes)[:-1]):
        projetos_cliente = df_projetos[df_projetos['Cliente'] == cliente]
        linha_separacao = projetos_cliente['Linha_global'].max() + 0.5
        plt.axhline(y=linha_separacao, color='lightgray', linestyle='-', 
                   linewidth=1, alpha=0.5)
    
    # Configurar eixo X
    plt.xlim(data_inicio_min, data_fim_max)
    plt.gca().xaxis.set_major_locator(mdates.MonthLocator())
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%b/%y'))
    plt.xticks(rotation=0, fontsize=9, color='gray')
    
    # Grid
    plt.grid(axis='x', linestyle='--', color='lightgray', linewidth=0.7, alpha=0.7)
    
    # Títulos e labels
    plt.title(titulo, fontsize=18, fontweight='bold', pad=20)
    plt.xlabel('Data', fontsize=12, fontweight='bold')
    plt.ylabel('Clientes', fontsize=12, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(arquivo_saida, dpi=300, bbox_inches='tight')
    plt.close()

# ============================
# EXECUÇÃO PRINCIPAL
# ============================

def gerar_para_web(arquivo_bytes):
    """Para uso no portal web. Retorna imagem PNG como string base64."""
    import io as _io, base64 as _b64, tempfile as _tmp

    with _tmp.NamedTemporaryFile(delete=False, suffix='.xlsx') as f:
        f.write(arquivo_bytes)
        tmp = f.name
    try:
        df = carregar_dados(tmp)
        clientes_projetos = extrair_clientes_projetos(df)
        if not clientes_projetos:
            raise ValueError('Nenhum cliente ou projeto encontrado')
        df_projetos = organizar_projetos_por_linha(clientes_projetos)
        if df_projetos.empty:
            raise ValueError('Nenhum projeto com datas válidas')
        clientes_unicos = sorted(df_projetos['Cliente'].unique())
        cores_dict = carregar_mapa_cores(ARQ_CORES_CLIENTES, cores_clientes_base, clientes_unicos)
        buf = _io.BytesIO()
        plotar_gantt_projetos(df_projetos, cores_dict, 'Cronograma de Projetos por Cliente', buf)
        buf.seek(0)
        return _b64.b64encode(buf.read()).decode('utf-8')
    finally:
        os.unlink(tmp)


if __name__ == "__main__":
    
    # Listar arquivos Excel disponíveis
    arquivos_xlsx = [f for f in os.listdir('.') if f.endswith('.xlsx')]
    
    if not arquivos_xlsx:
        print('Nenhum arquivo .xlsx encontrado na pasta.')
        exit()
    
    print('Arquivos Excel encontrados:')
    for i, nome_arq in enumerate(arquivos_xlsx, 1):
        print(f'{i} - {nome_arq}')
    
    escolha = int(input('\nDigite o número do arquivo desejado: '))
    arquivo = arquivos_xlsx[escolha - 1]
    
    # Carregar dados
    df = carregar_dados(arquivo)
    
    # Extrair estrutura de clientes e projetos
    clientes_projetos = extrair_clientes_projetos(df)
    
    if not clientes_projetos:
        print('ERRO: Nenhum cliente ou projeto encontrado!')
        print('Verifique se a coluna "Nível_da_estrutura_de_tópicos" existe e contém valores 1 e 2.')
        exit()
    
    # Organizar projetos em linhas
    df_projetos = organizar_projetos_por_linha(clientes_projetos)
    
    if df_projetos.empty:
        print('ERRO: Nenhum projeto com datas válidas encontrado!')
        exit()
    
    # Carregar cores
    clientes_unicos = sorted(df_projetos['Cliente'].unique())
    cores_dict = carregar_mapa_cores(ARQ_CORES_CLIENTES, cores_clientes_base, clientes_unicos)
    
    # Gerar gráfico
    plotar_gantt_projetos(
        df_projetos, 
        cores_dict, 
        'Cronograma de Projetos por Cliente', 
        'projetos.png'
    )
    
    print('Gráfico gerado com sucesso!')

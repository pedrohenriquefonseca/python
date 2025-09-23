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

# Paletas de cores expandidas (16 cores cada)
cores_horizontes_base = [
    '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#daa520',
    '#e377c2', '#7f7f7f', '#bcbd22', '#17becf', '#aec7e8', '#ffbb78',
    '#98df8a', '#ff9896', '#c5b0d5', '#c49c94'
]

cores_fornecedores_base = [
    '#17becf', '#bcbd22', '#e377c2', '#7f7f7f', '#aec7e8', '#f7b6d2',
    '#8c564b', '#9467bd', '#ff7f0e', '#1f77b4', '#ffbb78', '#98df8a',
    '#ff9896', '#c5b0d5', '#c49c94', '#2ca02c'
]

# Arquivos de mapeamento de cores persistente
ARQ_CORES_HORIZONTES = 'cores_horizontes.json'
ARQ_CORES_FORNECEDORES = 'cores_fornecedores.json'

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
    df = pd.read_excel(nome_arquivo, sheet_name='Tabela_Tarefas1')
    df['Início_en'] = df['Início'].apply(traduzir_meses)
    df['Término_en'] = df['Término'].apply(traduzir_meses)
    df['Início_dt'] = pd.to_datetime(df['Início_en'], errors='coerce', format='%d %B %Y %H:%M')
    df['Término_dt'] = pd.to_datetime(df['Término_en'], errors='coerce', format='%d %B %Y %H:%M')
    df = df.rename(columns={'Nome_da_Tarefa': 'Nome'})
    df = df[df['Ativo'] == 'Sim']
    return df

def preparar_grupo(df, grupo):
    df_grupo = df[df['Grupo_de_recursos'] == grupo].copy()
    df_grupo = df_grupo.assign(Nomes_dos_recursos=df_grupo['Nomes_dos_recursos'].str.split(';'))
    df_grupo = df_grupo.explode('Nomes_dos_recursos')
    df_grupo['Nomes_dos_recursos'] = df_grupo['Nomes_dos_recursos'].str.strip()
    return df_grupo

def empilhar_tarefas(df_grupo):
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
        with open(arq_json, 'r') as f:
            mapa = json.load(f)
    else:
        mapa = {}

    cores_disponiveis = [c for c in paleta_base if c not in mapa.values()]

    for recurso in recursos:
        if recurso not in mapa:
            if cores_disponiveis:
                mapa[recurso] = cores_disponiveis.pop(0)
            else:
                # Se esgotar a paleta, continua reaproveitando de forma circular
                mapa[recurso] = paleta_base[len(mapa) % len(paleta_base)]

    with open(arq_json, 'w') as f:
        json.dump(mapa, f, indent=4)

    return mapa

def plotar(df_aloc, recursos, cores_dict, titulo, arquivo_saida):
    hoje = datetime.now()
    data_inicio_min = df_aloc['Início'].min().replace(day=1)
    data_fim_max = df_aloc['Fim'].max().replace(day=1) + pd.offsets.MonthEnd(1)

    plt.figure(figsize=FIGSIZE)

    for _, row in df_aloc.iterrows():
        inicio, fim = row['Início'], row['Fim']
        duracao, y_pos = fim - inicio, row['Y_absoluto']
        cor = cores_dict[row['Recurso']]
        plt.barh(y=y_pos, width=duracao, left=inicio, height=0.7, align='center', color=cor)
        plt.text(inicio + duracao / 50, y_pos, row['Nome'], va='center', ha='left', fontsize=9, color='black')

    plt.axvline(x=hoje, color='red', linestyle='--', linewidth=1)
    plt.text(hoje, plt.ylim()[1], 'Hoje', color='red', va='bottom', ha='center', fontsize=10, fontweight='normal')

    y_labels, y_ticks, y_colors = [], [], []
    for recurso in recursos:
        posicoes = df_aloc[df_aloc['Recurso'] == recurso]['Y_absoluto'].values
        pos_central = (posicoes.min() + posicoes.max()) / 2
        y_labels.append(recurso)
        y_ticks.append(pos_central)
        y_colors.append(cores_dict[recurso])

    plt.yticks(y_ticks, y_labels, fontsize=10, fontweight='bold')
    ax = plt.gca()
    for ticklabel, color in zip(ax.get_yticklabels(), y_colors):
        ticklabel.set_color(color)

    plt.xlim(data_inicio_min, data_fim_max)
    plt.gca().xaxis.set_major_locator(mdates.MonthLocator())
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%b/%y'))
    plt.xticks(rotation=0, fontsize=10, color='gray')

    plt.grid(axis='x', linestyle='--', color='lightgray', linewidth=0.8)

    plt.title(titulo, fontsize=16, fontweight='bold', pad=20)
    plt.xlabel('Data', fontsize=11, fontweight='bold')
    plt.ylabel('Recursos', fontsize=11, fontweight='bold')

    plt.tight_layout()
    plt.savefig(arquivo_saida, dpi=300)
    plt.close()

# ============================
# EXECUÇÃO DO MOTOR
# ============================

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

    # --- Horizontes ---
    df_h = preparar_grupo(df, 'Horizontes')
    df_aloc_h, recursos_h = empilhar_tarefas(df_h)
    cores_dict_h = carregar_mapa_cores(ARQ_CORES_HORIZONTES, cores_horizontes_base, recursos_h)
    plotar(df_aloc_h, recursos_h, cores_dict_h, 'Relatório de Alocação de Equipe', 'horizontes.png')

    # --- Fornecedores ---
    df_f = preparar_grupo(df, 'Fornecedores')
    df_aloc_f, recursos_f = empilhar_tarefas(df_f)
    cores_dict_f = carregar_mapa_cores(ARQ_CORES_FORNECEDORES, cores_fornecedores_base, recursos_f)
    plotar(df_aloc_f, recursos_f, cores_dict_f, 'Relatório de Alocação de Fornecedores', 'fornecedores.png')

    print('Gráficos gerados com sucesso!')
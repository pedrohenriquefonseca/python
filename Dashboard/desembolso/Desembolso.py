import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import os

# --- FUNÇÃO DE NORMALIZAÇÃO DE DATAS ---

meses_pt_en = {
    'janeiro': 'January', 'fevereiro': 'February', 'março': 'March', 'abril': 'April',
    'maio': 'May', 'junho': 'June', 'julho': 'July', 'agosto': 'August',
    'setembro': 'September', 'outubro': 'October', 'novembro': 'November', 'dezembro': 'December'
}

def traduzir_data(data_str):
    for pt, en in meses_pt_en.items():
        data_str = data_str.lower().replace(pt, en)
    try:
        data = pd.to_datetime(data_str, errors='coerce')
        return data.strftime('%d/%m/%y') if pd.notnull(data) else None
    except Exception:
        return None

# --- FUNÇÃO PARA AJUSTAR O MÊS CUSTOMIZADO ---

def mes_customizado(data, dia_corte):
    '''
    Lógica customizada baseada no dia de corte definido pelo usuário:
    - Se dia <= dia_corte: valor fica no MÊS ATUAL
    - Se dia > dia_corte: valor vai para o MÊS SEGUINTE
    '''
    if pd.isnull(data):
        return None

    if data.day > dia_corte:
        # Vai para o mês seguinte
        if data.month == 12:
            return pd.Timestamp(data.year + 1, 1, 1)
        else:
            return pd.Timestamp(data.year, data.month + 1, 1)
    else:
        # Fica no mês atual
        return pd.Timestamp(data.year, data.month, 1)

# --- RESOLUÇÃO DE SOBREPOSIÇÃO DE RÓTULOS ---

def resolver_sobreposicao(fig, textos, max_iter=60):
    """Detecta sobreposição entre rótulos e ajusta suas posições verticalmente."""
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    for _ in range(max_iter):
        modificado = False
        for i in range(len(textos)):
            for j in range(i + 1, len(textos)):
                t1, t2 = textos[i], textos[j]
                bb1 = t1.get_window_extent(renderer=renderer)
                bb2 = t2.get_window_extent(renderer=renderer)
                if bb1.overlaps(bb2):
                    overlap_px = min(bb1.y1, bb2.y1) - max(bb1.y0, bb2.y0)
                    if overlap_px > 0:
                        ax_t1 = t1.axes
                        ax_t2 = t2.axes
                        dy1 = abs(ax_t1.transData.inverted().transform((0, overlap_px / 2 + 2))[1] -
                                  ax_t1.transData.inverted().transform((0, 0))[1])
                        dy2 = abs(ax_t2.transData.inverted().transform((0, overlap_px / 2 + 2))[1] -
                                  ax_t2.transData.inverted().transform((0, 0))[1])
                        x1, y1 = t1.get_position()
                        x2, y2 = t2.get_position()
                        if y1 >= y2:
                            t1.set_position((x1, y1 + dy1))
                            t2.set_position((x2, y2 - dy2))
                        else:
                            t1.set_position((x1, y1 - dy1))
                            t2.set_position((x2, y2 + dy2))
                        fig.canvas.draw()
                        modificado = True
        if not modificado:
            break

# --- PROCESSAMENTO E GRÁFICO ---

def plotar_desembolso(arquivo_path, nome_projeto, dia_corte):
    """Processa o arquivo Excel e exibe o gráfico de desembolso."""
    xls = pd.ExcelFile(arquivo_path)
    primeira_aba = xls.sheet_names[0]
    df = pd.read_excel(xls, sheet_name=primeira_aba)

    colunas_necessarias = ['Ativo', 'Nível_da_estrutura_de_tópicos', 'Término', 'Custo']
    faltando = [c for c in colunas_necessarias if c not in df.columns]
    if faltando:
        raise ValueError(f"Planilha incompatível. Colunas ausentes: {', '.join(faltando)}")

    tem_receita = 'Receita' in df.columns and pd.to_numeric(df['Receita'], errors='coerce').fillna(0).sum() > 0

    df = df[
        (df['Ativo'] == 'Sim') &
        (df['Nível_da_estrutura_de_tópicos'] == 4)
    ].copy()

    df['Término'] = df['Término'].astype(str).apply(traduzir_data)
    df['Término'] = pd.to_datetime(df['Término'], format='%d/%m/%y', errors='coerce')
    df['Custo'] = pd.to_numeric(df['Custo'], errors='coerce')
    if tem_receita:
        df['Receita'] = pd.to_numeric(df['Receita'], errors='coerce')

    # Agrupamento com lógica customizada
    df['Mês_Custom'] = df['Término'].apply(lambda x: mes_customizado(x, dia_corte))
    colunas_group = ['Custo', 'Receita'] if tem_receita else ['Custo']
    df_mensal = df.groupby('Mês_Custom')[colunas_group].sum().reset_index()
    df_mensal = df_mensal[df_mensal['Custo'] > 0].reset_index(drop=True)
    df_mensal['Custo'] = df_mensal['Custo'].fillna(0)
    df_mensal['Custo_Acumulado'] = df_mensal['Custo'].cumsum()
    if tem_receita:
        df_mensal['Receita']          = df_mensal['Receita'].fillna(0)
        df_mensal['Receita_Acumulada'] = df_mensal['Receita'].cumsum()

    # --- GRÁFICO ---

    x = range(len(df_mensal))

    fig, ax1 = plt.subplots(figsize=(12, 6))

    largura_barra = 0.4
    COR_TEXTO        = '#000000'
    COR_LINHA        = '#666666'
    COR_AMARELO      = '#fca903'
    COR_LARANJA      = '#E87722'
    COR_BARRA_RECEITA = '#cccccc'
    COR_BARRA_CUSTO   = '#999999'

    # Barras mensais
    if tem_receita:
        bars_receita = ax1.bar([i - largura_barra/2 for i in x], df_mensal['Receita'], width=largura_barra, color=COR_BARRA_RECEITA, label='Receita Mensal', zorder=2)
        bars_custo   = ax1.bar([i + largura_barra/2 for i in x], df_mensal['Custo'],   width=largura_barra, color=COR_BARRA_CUSTO,   label='Custo Mensal',   zorder=2)
    else:
        bars_custo = ax1.bar(list(x), df_mensal['Custo'], width=largura_barra, color=COR_BARRA_RECEITA, label='Receita Mensal', zorder=2)

    # Rótulos verticais dentro das barras — alinhados pelo pé do gráfico
    col_max = df_mensal['Receita'].max() if tem_receita else 0
    col_max = max(col_max, df_mensal['Custo'].max())
    offset_bar = col_max * 0.01

    if tem_receita:
        for bar, valor in zip(bars_receita, df_mensal['Receita']):
            if valor > 0:
                ax1.text(bar.get_x() + bar.get_width()/2, offset_bar,
                         f'R$ {int(valor):,}'.replace(',', '.'),
                         ha='center', va='bottom', fontsize=6, rotation=90, color=COR_TEXTO)
    for bar, valor in zip(bars_custo, df_mensal['Custo']):
        if valor > 0:
            ax1.text(bar.get_x() + bar.get_width()/2, offset_bar,
                     f'R$ {int(valor):,}'.replace(',', '.'),
                     ha='center', va='bottom', fontsize=6, rotation=90, color=COR_TEXTO)

    # Curvas acumuladas
    ax2 = ax1.twinx()
    if tem_receita:
        ax2.plot(list(x), df_mensal['Receita_Acumulada'], marker='o', color=COR_AMARELO, markerfacecolor=COR_AMARELO, markeredgecolor=COR_AMARELO, label='Receita Acumulada', zorder=3)
        ax2.plot(list(x), df_mensal['Custo_Acumulado'],   marker='o', color=COR_LARANJA, markerfacecolor=COR_LARANJA, markeredgecolor=COR_LARANJA, label='Custos Acumulados', zorder=3)
    else:
        ax2.plot(list(x), df_mensal['Custo_Acumulado'], marker='o', color=COR_AMARELO, markerfacecolor=COR_AMARELO, markeredgecolor=COR_AMARELO, label='Receita Acumulada', zorder=3)

    # Rótulos dos nós das curvas
    max_valor = df_mensal['Receita_Acumulada'].max() if tem_receita else df_mensal['Custo_Acumulado'].max()
    offset = max_valor * 0.02
    textos_nos = []
    if tem_receita:
        for i, y in enumerate(df_mensal['Receita_Acumulada']):
            t = ax2.text(i, y + offset, f'R$ {int(y):,}'.replace(',', '.'), fontsize=6, rotation=0, va='bottom', ha='center', color=COR_TEXTO)
            textos_nos.append(t)
    for i, y in enumerate(df_mensal['Custo_Acumulado']):
        t = ax2.text(i, y + offset, f'R$ {int(y):,}'.replace(',', '.'), fontsize=6, rotation=0, va='bottom', ha='center', color=COR_TEXTO)
        textos_nos.append(t)

    # Resolve sobreposições dos rótulos
    resolver_sobreposicao(fig, textos_nos)

    # Legenda
    handles1, labels1 = ax1.get_legend_handles_labels()
    handles2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(handles1 + handles2, labels1 + labels2, loc='upper left', fontsize=8)

    # Rótulos dos eixos
    ax1.set_ylabel('Desembolso Mensal', fontsize=9, fontweight='bold')
    ax2.set_ylabel('Desembolso Acumulado', fontsize=9, fontweight='bold')

    # Formatadores de valores nos eixos Y
    ax1.yaxis.set_major_formatter(mtick.StrMethodFormatter('R$ {x:,.0f}'))
    ax2.yaxis.set_major_formatter(mtick.StrMethodFormatter('R$ {x:,.0f}'))

    # Fonte menor para valores dos eixos
    ax1.tick_params(axis='y', labelsize=7)
    ax2.tick_params(axis='y', labelsize=7)

    # Eixo X com espaçamento igualitário
    ax1.set_xticks(range(len(df_mensal)))

    # Criar lista de labels para o eixo X
    labels_x = []
    for d in df_mensal['Mês_Custom']:
        label = d.strftime('%b-%y').capitalize()
        labels_x.append(label)
    ax1.set_xticklabels(labels_x, fontsize=7)

    # Grade tracejada
    ax1.grid(True, which='major', axis='both', linestyle='--', linewidth=0.5, color='lightgray')
    ax2.grid(False)

    # Título principal no topo do eixo e subtítulo logo abaixo, ambos próximos ao gráfico
    ax1.set_title(f'Curva de Desembolso - {nome_projeto}', fontsize=12, fontweight='bold', pad=20)
    ax1.text(0.5, 1.01, f'(Corte no dia {dia_corte})', transform=ax1.transAxes, ha='center', va='bottom', fontsize=9, fontweight='normal')
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.show()


if __name__ == '__main__':
    # --- SELEÇÃO DO ARQUIVO E NOME DO PROJETO ---

    arquivos_excel = []
    for f in os.listdir():
        if f.lower().endswith(('.xls', '.xlsx')):
            arquivos_excel.append(f)

    if not arquivos_excel:
        print('Nenhum arquivo Excel (.xls ou .xlsx) encontrado na pasta.')
        exit()

    # Seleção automática se houver apenas um arquivo Excel
    if len(arquivos_excel) == 1:
        arquivo_escolhido = arquivos_excel[0]
        print(f'Arquivo selecionado automaticamente: {arquivo_escolhido}')
    else:
        # Se houver múltiplos arquivos, pedir ao usuário para escolher
        print('Arquivos disponíveis:')
        for i, nome in enumerate(arquivos_excel):
            print(f'{i + 1}. {nome}')

        indice = int(input('Digite o número do arquivo que deseja usar: ')) - 1
        if indice < 0 or indice >= len(arquivos_excel):
            print('Opção inválida.')
            exit()

        arquivo_escolhido = arquivos_excel[indice]

    nome_projeto = input('Digite o nome do projeto para o título do gráfico: ').strip()

    # --- SOLICITAÇÃO DA DATA DE CORTE ---
    while True:
        try:
            dia_corte = int(input('Digite o dia de corte para agrupamento mensal (1-31): '))
            if 1 <= dia_corte <= 31:
                break
            else:
                print('Por favor, digite um número entre 1 e 31.')
        except ValueError:
            print('Por favor, digite um número válido.')

    plotar_desembolso(arquivo_escolhido, nome_projeto, dia_corte)

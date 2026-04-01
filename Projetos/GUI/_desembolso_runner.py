"""
Runner isolado para a Curva de Desembolso.
Executado como subprocesso pelo app.py para abrir o gráfico em janela própria do matplotlib.
Uso: python _desembolso_runner.py <caminho_xlsx> <nome_projeto> <dia_corte>
"""
import sys
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick

MESES = {
    'janeiro': 'January', 'fevereiro': 'February', 'março': 'March',
    'abril': 'April', 'maio': 'May', 'junho': 'June', 'julho': 'July',
    'agosto': 'August', 'setembro': 'September', 'outubro': 'October',
    'novembro': 'November', 'dezembro': 'December'
}

def traduzir_data(data_str):
    s = str(data_str).lower()
    for pt, en in MESES.items():
        s = s.replace(pt, en)
    try:
        data = pd.to_datetime(s, errors='coerce')
        return data.strftime('%d/%m/%y') if pd.notnull(data) else None
    except Exception:
        return None

def mes_customizado(data, dia_corte):
    if pd.isnull(data):
        return None
    if data.day > dia_corte:
        if data.month == 12:
            return pd.Timestamp(data.year + 1, 1, 1)
        return pd.Timestamp(data.year, data.month + 1, 1)
    return pd.Timestamp(data.year, data.month, 1)

if __name__ == '__main__':
    arquivo, nome_projeto, dia_corte = sys.argv[1], sys.argv[2], int(sys.argv[3])

    xls = pd.ExcelFile(arquivo)
    df = pd.read_excel(xls, sheet_name=xls.sheet_names[0])

    df = df[(df['Ativo'] == 'Sim') & (df['Nível_da_estrutura_de_tópicos'] == 4)].copy()
    df['Término'] = df['Término'].astype(str).apply(traduzir_data)
    df['Término'] = pd.to_datetime(df['Término'], format='%d/%m/%y', errors='coerce')
    df['Custo'] = pd.to_numeric(df['Custo'], errors='coerce')

    df['Mês_Custom'] = df['Término'].apply(lambda x: mes_customizado(x, dia_corte))
    df_m = df.groupby('Mês_Custom')['Custo'].sum().reset_index()
    df_m = df_m[df_m['Custo'] > 0]
    df_m['Acumulado'] = df_m['Custo'].cumsum()

    fig, ax1 = plt.subplots(figsize=(12, 6))
    bars = ax1.bar(range(len(df_m)), df_m['Custo'], width=0.6, color='lightgray')
    for bar, valor in zip(bars, df_m['Custo']):
        ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_y() + 50,
                 f'R$ {int(valor):,}'.replace(',', '.'), ha='center', va='bottom', fontsize=7)

    ax2 = ax1.twinx()
    ax2.plot(range(len(df_m)), df_m['Acumulado'], marker='o', color='#fca903')
    offset = df_m['Acumulado'].max() * 0.02
    for i, y in enumerate(df_m['Acumulado']):
        ax2.text(i, y + offset, f'R$ {int(y):,}'.replace(',', '.'),
                 fontsize=8, rotation=90, va='bottom', ha='center')

    ax1.set_ylabel('Desembolso Mensal', fontsize=9, fontweight='bold')
    ax2.set_ylabel('Desembolso Acumulado', fontsize=9, fontweight='bold')
    ax1.yaxis.set_major_formatter(mtick.StrMethodFormatter('R$ {x:,.0f}'))
    ax2.yaxis.set_major_formatter(mtick.StrMethodFormatter('R$ {x:,.0f}'))
    ax1.tick_params(axis='y', labelsize=7)
    ax2.tick_params(axis='y', labelsize=7)
    ax1.set_xticks(range(len(df_m)))
    ax1.set_xticklabels([d.strftime('%b-%y').capitalize() for d in df_m['Mês_Custom']], fontsize=7)
    ax1.grid(True, which='major', axis='both', linestyle='--', linewidth=0.5, color='lightgray')
    ax2.grid(False)
    ax1.set_title(f'Curva de Desembolso — {nome_projeto}', fontsize=12, fontweight='bold', pad=20)
    ax1.text(0.5, 1.01, f'(Corte no dia {dia_corte})', transform=ax1.transAxes,
             ha='center', va='bottom', fontsize=9)
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.show()

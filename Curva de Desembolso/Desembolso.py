import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import os

# --- SELEÇÃO DO ARQUIVO E NOME DO PROJETO ---

arquivos_excel = []
for f in os.listdir():
    if f.lower().endswith(('.xls', '.xlsx')):
        arquivos_excel.append(f)

if not arquivos_excel:
    print('Nenhum arquivo Excel (.xls ou .xlsx) encontrado na pasta.')
    exit()

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

# --- PROCESSAMENTO DOS DADOS ---

try:
    xls = pd.ExcelFile(arquivo_escolhido)
    primeira_aba = xls.sheet_names[0]
    df = pd.read_excel(xls, sheet_name=primeira_aba)
except Exception as e:
    print(f'Erro ao ler o arquivo: {e}')
    exit()

df = df[
    (df['Ativo'] == 'Sim') &
    (df['Nível_da_estrutura_de_tópicos'] == 4)
].copy()

df['Término'] = df['Término'].astype(str).apply(traduzir_data)
df['Término'] = pd.to_datetime(df['Término'], format='%d/%m/%y', errors='coerce')
df['Custo'] = pd.to_numeric(df['Custo'], errors='coerce')

# Agrupamento com lógica customizada
df['Mês_Custom'] = df['Término'].apply(lambda x: mes_customizado(x, dia_corte))
df_mensal = df.groupby('Mês_Custom')['Custo'].sum().reset_index()
df_mensal = df_mensal[df_mensal['Custo'] > 0]
df_mensal['Acumulado'] = df_mensal['Custo'].cumsum()

# --- GRÁFICO ---

fig, ax1 = plt.subplots(figsize=(12, 6))

# Barras mensais
bars = ax1.bar(range(len(df_mensal)), df_mensal['Custo'], width=0.6, color='lightgray')

# Rótulos dos valores mensais na parte inferior das barras
for i, (bar, valor) in enumerate(zip(bars, df_mensal['Custo'])):
    ax1.text(bar.get_x() + bar.get_width()/2, bar.get_y() + 50, 
             f'R$ {int(valor):,}'.replace(',', '.'), 
             ha='center', va='bottom', fontsize=7)

# Linha acumulada com cor #fca903
ax2 = ax1.twinx()
ax2.plot(range(len(df_mensal)), df_mensal['Acumulado'], marker='o', color='#fca903')

# Rótulos acumulados
max_valor = df_mensal['Acumulado'].max()
offset = max_valor * 0.02  
for i, y in enumerate(df_mensal['Acumulado']):
    ax2.text(i, y + offset, f'R$ {int(y):,}'.replace(',', '.'), fontsize=8, rotation=90, va='bottom', ha='center')

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
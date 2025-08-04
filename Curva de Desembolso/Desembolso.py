import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import os

# --- SELEÇÃO DO ARQUIVO E NOME DO PROJETO ---

arquivos_excel = [f for f in os.listdir() if f.lower().endswith(('.xls', '.xlsx'))]

if not arquivos_excel:
    print("Nenhum arquivo Excel (.xls ou .xlsx) encontrado na pasta.")
    exit()

print("Arquivos disponíveis:")
for i, nome in enumerate(arquivos_excel):
    print(f"{i + 1}. {nome}")

indice = int(input("Digite o número do arquivo que deseja usar: ")) - 1
if indice < 0 or indice >= len(arquivos_excel):
    print("Opção inválida.")
    exit()

arquivo_escolhido = arquivos_excel[indice]
nome_projeto = input("Digite o nome do projeto para o título do gráfico: ").strip()

# --- FUNÇÃO DE NORMALIZAÇÃO DE DATAS ---

meses_pt_en = {
    "janeiro": "January", "fevereiro": "February", "março": "March", "abril": "April",
    "maio": "May", "junho": "June", "julho": "July", "agosto": "August",
    "setembro": "September", "outubro": "October", "novembro": "November", "dezembro": "December"
}

def traduzir_data(data_str):
    for pt, en in meses_pt_en.items():
        data_str = data_str.lower().replace(pt, en)
    try:
        data = pd.to_datetime(data_str, errors='coerce')
        return data.strftime("%d/%m/%y") if pd.notnull(data) else None
    except Exception:
        return None

# --- FUNÇÃO PARA AJUSTAR O MÊS CUSTOMIZADO ---

def mes_customizado(data):
    if pd.isnull(data):
        return None
    if data.day >= 21:
        return pd.Timestamp(data.year, data.month, 21)
    else:
        if data.month == 1:
            return pd.Timestamp(data.year - 1, 12, 21)
        else:
            return pd.Timestamp(data.year, data.month - 1, 21)

# --- PROCESSAMENTO DOS DADOS ---

try:
    xls = pd.ExcelFile(arquivo_escolhido)
    primeira_aba = xls.sheet_names[0]
    df = pd.read_excel(xls, sheet_name=primeira_aba)
except Exception as e:
    print(f"Erro ao ler o arquivo: {e}")
    exit()

df = df[
    (df["Ativo"] == "Sim") &
    (df["Nível_da_estrutura_de_tópicos"] == 4)
].copy()

df["Término"] = df["Término"].astype(str).apply(traduzir_data)
df["Término"] = pd.to_datetime(df["Término"], format="%d/%m/%y", errors="coerce")
df["Custo"] = pd.to_numeric(df["Custo"], errors="coerce")

# Agrupamento considerando meses iniciando em 21 e terminando em 20
df["Mês_Custom"] = df["Término"].apply(mes_customizado)
df_mensal = df.groupby("Mês_Custom")["Custo"].sum().reset_index()
df_mensal = df_mensal[df_mensal["Custo"] > 0]
df_mensal["Acumulado"] = df_mensal["Custo"].cumsum()

# --- GRÁFICO ---

fig, ax1 = plt.subplots(figsize=(12, 6))

# Barras mensais
ax1.bar(range(len(df_mensal)), df_mensal["Custo"], width=0.6, color='lightgray')

# Linha acumulada com cor #fca903
ax2 = ax1.twinx()
ax2.plot(range(len(df_mensal)), df_mensal["Acumulado"], marker='o', color='#fca903')

# Rótulos acumulados
for i, y in enumerate(df_mensal["Acumulado"]):
    ax2.text(i, y, f'R$ {int(y):,}'.replace(",", "."), fontsize=8, rotation=90, va='bottom', ha='center')

# Rótulos dos eixos
ax1.set_ylabel("Desembolso Mensal", fontsize=9, fontweight="bold")
ax2.set_ylabel("Desembolso Acumulado", fontsize=9, fontweight="bold")

# Formatadores de valores nos eixos Y
ax1.yaxis.set_major_formatter(mtick.StrMethodFormatter('R$ {x:,.0f}'))
ax2.yaxis.set_major_formatter(mtick.StrMethodFormatter('R$ {x:,.0f}'))

# Fonte menor para valores dos eixos
ax1.tick_params(axis='y', labelsize=7)
ax2.tick_params(axis='y', labelsize=7)

# Eixo X com espaçamento igualitário
ax1.set_xticks(range(len(df_mensal)))
ax1.set_xticklabels([d.strftime('%b-%y').capitalize() for d in df_mensal["Mês_Custom"]], fontsize=7)

# Grade tracejada
ax1.grid(True, which='major', axis='both', linestyle='--', linewidth=0.5, color='lightgray')
ax2.grid(False)

# Título
plt.title(f"Curva de Desembolso - {nome_projeto}", fontsize=12, fontweight="bold")
plt.tight_layout()
plt.show()

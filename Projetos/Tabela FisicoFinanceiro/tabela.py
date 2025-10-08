import pandas as pd
import glob
from datetime import datetime

# Solicitar informações do usuário
nome_projeto = input("Digite o nome do projeto: ")
dia_corte = int(input("Digite o dia de corte do projeto (de 01 a 31): "))

# Buscar arquivos xlsx na pasta raiz
arquivos_xlsx = glob.glob("*.xlsx")

if len(arquivos_xlsx) == 0:
    print("Erro: Nenhum arquivo .xlsx encontrado na pasta raiz")
    exit()
elif len(arquivos_xlsx) == 1:
    arquivo_entrada = arquivos_xlsx[0]
    print(f"Usando arquivo: {arquivo_entrada}")
else:
    print("\nArquivos .xlsx encontrados:")
    for i, arquivo in enumerate(arquivos_xlsx, 1):
        print(f"{i}. {arquivo}")
    escolha = int(input("\nEscolha o número do arquivo: "))
    arquivo_entrada = arquivos_xlsx[escolha - 1]

# Ler arquivo Excel
df = pd.read_excel(arquivo_entrada)

# Aplicar filtros
df = df[df['Nível_da_estrutura_de_tópicos'] == 4]
df = df[df['Ativo'] == 'Sim']

# Substituir valores nulos por 0
df['Custo'] = df['Custo'].fillna(0)

# Função para converter data em português
def parse_data_portugues(data_str):
    meses = {
        'janeiro': 1, 'fevereiro': 2, 'março': 3, 'abril': 4,
        'maio': 5, 'junho': 6, 'julho': 7, 'agosto': 8,
        'setembro': 9, 'outubro': 10, 'novembro': 11, 'dezembro': 12
    }
    partes = data_str.split()
    dia = int(partes[0])
    mes = meses[partes[1].lower()]
    ano = int(partes[2])
    return datetime(ano, mes, dia)

# Converter coluna Término para datetime
df['Data'] = df['Término'].apply(parse_data_portugues)

# Calcular mês de competência
def calcular_competencia(data, dia_corte):
    if data.day < dia_corte:
        return data
    else:
        if data.month == 12:
            return datetime(data.year + 1, 1, 1)
        else:
            return datetime(data.year, data.month + 1, 1)

df['Competencia'] = df['Data'].apply(lambda x: calcular_competencia(x, dia_corte))
df['Mes_Ano'] = df['Competencia'].dt.strftime('%m/%Y')

# Extrair 2 primeiros dígitos do código
df['COD_2_DIGITOS'] = df['COD_TAREFA_AUX'].astype(str).str[:2]

# Criar tabela pivot
tabela_resumo = df.pivot_table(
    index='COD_2_DIGITOS',
    columns='Mes_Ano',
    values='Custo',
    aggfunc='sum',
    fill_value=0
)
tabela_resumo.index.name = "Código"
# Ordenar colunas por data
colunas_ordenadas = sorted(tabela_resumo.columns, key=lambda x: datetime.strptime(x, '%m/%Y'))
tabela_resumo = tabela_resumo[colunas_ordenadas]

# Salvar em Excel
nome_saida = f"Relatório Físico Financeiro {nome_projeto}.xlsx"
tabela_resumo.to_excel(nome_saida)

print(f"\nRelatório gerado com sucesso: {nome_saida}")
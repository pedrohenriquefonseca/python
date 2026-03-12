import os
import pandas as pd
from datetime import datetime

#Seleciona arquivo Excel da pasta atual.
def selecionar_arquivo_excel():
    arquivos = []
    for arquivo in os.listdir():
        if arquivo.endswith(('.xls', '.xlsx')):
            arquivos.append(arquivo)
    
    if not arquivos:
        raise FileNotFoundError('Nenhum arquivo Excel encontrado na pasta atual.')
    elif len(arquivos) == 1:
        print(f'Arquivo selecionado automaticamente: {arquivos[0]}')
        return arquivos[0]
    else:
        print('Selecione um arquivo:')
        for idx, arquivo in enumerate(arquivos, 1):
            print(f'{idx}. {arquivo}')
        
        while True:
            try:
                escolha = int(input('Digite o número do arquivo desejado: '))
                if 1 <= escolha <= len(arquivos):
                    return arquivos[escolha - 1]
                else:
                    print(f'Por favor, digite um número entre 1 e {len(arquivos)}')
            except ValueError:
                print('Por favor, digite apenas números')
            except KeyboardInterrupt:
                print('\nOperação cancelada pelo usuário.')
                exit(1)


# Dicionário para tradução de meses
meses_portugues = {
    'janeiro': 'January', 'fevereiro': 'February', 'março': 'March', 'abril': 'April',
    'maio': 'May', 'junho': 'June', 'julho': 'July', 'agosto': 'August',
    'setembro': 'September', 'outubro': 'October', 'novembro': 'November', 'dezembro': 'December'
}

#Traduz nomes de meses do português para inglês.
def traduzir_meses(texto):
    if pd.isna(texto):
        return texto
    
    texto_lower = str(texto).lower()
    for pt, en in meses_portugues.items():
        texto_lower = texto_lower.replace(pt, en)
    return texto_lower

#Formata coluna de datas para o padrão brasileiro.
def formatar_data(coluna):
    try:
        datas_traduzidas = coluna.apply(traduzir_meses)
        datas_convertidas = pd.to_datetime(
            datas_traduzidas, 
            format='%d %B %Y %H:%M', 
            errors='coerce'
        )
        return datas_convertidas.dt.strftime('%d/%m/%y')
    except Exception as e:
        print(f'Aviso: Erro ao formatar datas: {e}')
        return coluna

#Calcula diferença em dias entre duas datas.
def calcular_dias_diferenca(data1, data2):
    if pd.isna(data1) or pd.isna(data2):
        return 0
    try:
        return (data1 - data2).days
    except:
        return 0

#Busca a hierarquia (bisavô, avô, pai) de uma linha específica.
def buscar_hierarquia(df, linha_index):
    pai = avo = bisavo = ''
    
    for i in range(linha_index - 1, -1, -1):
        if i < 0 or i >= len(df):
            continue
            
        try:
            nivel = df.at[i, 'Nível_da_estrutura_de_tópicos']
            nome = str(df.at[i, 'Nome'])
            
            if nivel == 3 and not pai:
                pai = nome
            elif nivel == 2 and not avo:
                avo = nome
            elif nivel == 1 and not bisavo:
                bisavo = nome
            
            if pai and avo and bisavo:
                break
        except (KeyError, IndexError):
            continue
    
    return bisavo, avo, pai

#Filtra tarefas baseado no recurso especificado.
def filtrar_tarefas_por_recurso(df, termo_busca):
    try:
        filtro_recursos = df['Nomes_dos_Recursos'].astype(str).str.contains(termo_busca, case=False, na=False)
        filtro_percentual = (df['Porcentagem_Concluída'] > 0) & (df['Porcentagem_Concluída'] < 1)
        return df[filtro_recursos & filtro_percentual]
    except KeyError:
        print(f'Aviso: Coluna necessária não encontrada para filtrar {termo_busca}')
        return pd.DataFrame()


def montar_secao_markdown(titulo, tarefas_df, df_principal, hoje, tipo_secao):
    #Monta uma seção em Markdown com as tarefas especificadas.
    secao_md = f'\n{titulo}'
    if tarefas_df.empty:
        secao_md += '- Não existem tarefas que cumpram os critérios desta seção\n'
        return secao_md

    grupos = {}
    for idx, row in tarefas_df.iterrows():
        bisavo, avo, pai = buscar_hierarquia(df_principal, idx)
        chave = bisavo if bisavo else 'Sem categoria'

        if tipo_secao == 'emissoes':
            linha = f'{avo} - {pai} - {row["Nome"]}: Programado para {row.get("Término", "N/A")}'
        else:
            dias_analise = '?'
            if pd.notna(row.get('Início_DT')):
                try:
                    dias_analise = (hoje - row['Início_DT']).days
                except:
                    dias_analise = '?'
            linha = f'{avo} - {pai} - {row["Nome"]}: A cargo do cliente desde {row.get("Início", "N/A")} ({dias_analise} dias)'

        grupos.setdefault(chave, []).append(linha)

    for bisavo, tarefas in grupos.items():
        if bisavo:
            secao_md += f'\n{bisavo}:\n'
        for tarefa in tarefas:
            secao_md += f'- {tarefa}\n'

    return secao_md

#Valida se as colunas necessárias existem no DataFrame.
def validar_colunas_necessarias(df):
    colunas_obrigatorias = [
        'Nível_da_estrutura_de_tópicos', 'Nome', 'Nomes_dos_Recursos',
        'Porcentagem_Concluída'
    ]
    
    colunas_faltantes = []
    for coluna in colunas_obrigatorias:
        if coluna not in df.columns:
            colunas_faltantes.append(coluna)
    
    if colunas_faltantes:
        print(f'Aviso: Colunas não encontradas: {", ".join(colunas_faltantes)}')
        # Criar colunas com valores padrão
        for coluna in colunas_faltantes:
            if 'Porcentagem' in coluna:
                df[coluna] = 0
            else:
                df[coluna] = ''
    
    return df

#Gera o relatório semanal diretamente em arquivo Markdown (.md).
def gerar_relatorio(nome_projeto):
    try:
        # Selecionar e carregar arquivo
        arquivo = selecionar_arquivo_excel()
        df = pd.read_excel(arquivo)
        
        if df.empty:
            raise ValueError('O arquivo Excel está vazio')
        
        # Validar colunas necessárias
        df = validar_colunas_necessarias(df)
        
        # Processar colunas de data
        col_datas = ['Início', 'Término', 'Início_da_Linha_de_Base', 'Término_da_linha_de_base']
        for col in col_datas:
            if col in df.columns:
                df[col] = formatar_data(df[col])
                # Criar versões datetime das colunas
                df[col + '_DT'] = pd.to_datetime(df[col], format='%d/%m/%y', errors='coerce')
        
        # Obter data atual
        hoje = datetime.now()
        hoje_fmt = hoje.strftime('%d/%m/%y')
        
        # Encontrar linha de nível 0 (projeto principal)
        nivel0_linhas = df[df['Nível_da_estrutura_de_tópicos'] == 0]
        if nivel0_linhas.empty:
            print('Aviso: Nenhuma linha de nível 0 encontrada. Usando primeira linha.')
            nivel0 = df.iloc[0]
        else:
            nivel0 = nivel0_linhas.iloc[0]
        
        # Calcular métricas do projeto
        AA = nivel0.get('Término', 'N/A')
        BB = calcular_dias_diferenca(nivel0.get('Término_DT'), nivel0.get('Término_da_linha_de_base_DT'))
        CC = nivel0.get('Término_da_linha_de_base', 'N/A')
        DD = calcular_dias_diferenca(nivel0.get('Término_da_linha_de_base_DT'), nivel0.get('Início_da_Linha_de_Base_DT'))
        EE = calcular_dias_diferenca(nivel0.get('Término_DT'), nivel0.get('Início_DT'))
        

        # Filtrar tarefas
        filtro_horizontes = filtrar_tarefas_por_recurso(df, 'Horizontes')
        filtro_cliente = filtrar_tarefas_por_recurso(df, 'Cliente')
        
        # Montar conteúdo Markdown
        partes = []
        partes.append(f'REPORT SEMANAL {nome_projeto.upper()} - {hoje_fmt}\n')
        partes.append('📌 RESUMO:\n')

        resumo_textos = [
            f'Previsão de Conclusão: {AA}, com desvio de {BB} dias corridos em relação à Linha de Base ({CC}).',
            f'Duração atual estimada: {EE+1} dias corridos (Linha de Base = {DD} dias corridos).'
        ]
        for texto in resumo_textos:
            partes.append(f'- {texto}\n')

        partes.append(
            montar_secao_markdown(
                '📅 PRÓXIMAS EMISSÕES DE PROJETO:',
                filtro_horizontes, df, hoje, 'emissoes'
            )
        )

        partes.append(
            montar_secao_markdown(
                '🔎 TAREFAS A CARGO DO CLIENTE:',
                filtro_cliente, df, hoje, 'analise'
            )
        )

        conteudo_md = ''.join(partes)

        # Salvar arquivo Markdown (sem data no nome)
        nome_arquivo = f'Relatório Semanal - {nome_projeto}.md'
        with open(nome_arquivo, 'w', encoding='utf-8') as f:
            f.write(conteudo_md)
        print(f'Relatório salvo como: {nome_arquivo}\n')
        
    except FileNotFoundError as e:
        print(f'Erro: {e}')
    except Exception as e:
        print(f'Erro inesperado: {e}')
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    try:
        projeto = input('\nDigite o nome do projeto: ').strip()
        if not projeto:
            print('Nome do projeto é obrigatório.')
            exit(1)
        gerar_relatorio(projeto)
    except KeyboardInterrupt:
        print('\nOperação cancelada pelo usuário.')
    except Exception as e:
        print(f'Erro na execução: {e}')
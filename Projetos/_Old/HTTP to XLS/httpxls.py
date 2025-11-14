import pandas as pd
import requests
import os
from io import StringIO
import xlsxwriter 
from urllib.parse import urlparse

def extrair_tabela_web_simples():
    """
    Extrai a tabela, ignora hiperlinks e salva no Excel usando Pandas/xlsxwriter.
    O foco é a extração de texto limpo e a aplicação de quebra de linha.
    """
    
    url = input("Por favor, digite o link (URL) da página da web que contém a tabela: ").strip()
    
    if not url.startswith('http'):
        print("❌ URL inválida. O link deve começar com 'http' ou 'https'.")
        return

    nome_arquivo = input("Por favor, digite o nome do arquivo de saída (ex: dados.xlsx): ").strip()
    
    if not nome_arquivo.lower().endswith('.xlsx'):
        nome_arquivo = f"{nome_arquivo.split('.')[0]}.xlsx"
        
    print(f"\nIniciando a extração simples da tabela da URL: {url}")
    
    try:
        # 1. Obter o conteúdo HTML
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        # 2. Usar pandas.read_html para analisar o HTML
        # O flavor='bs4' é mantido para melhor compatibilidade com o HTML do TST
        # O `keep_default_na=False` ajuda a evitar que o Pandas interprete strings vazias como NaN
        tabelas = pd.read_html(StringIO(response.text), header=0, flavor='bs4', keep_default_na=False) 

        if not tabelas:
            print("❌ Nenhuma tabela HTML encontrada na página.")
            return

        # 3. Selecionar a maior tabela (presumida como principal)
        tabela_principal = max(tabelas, key=lambda df: df.size)
        
        # 4. Limpeza e Preparação dos Dados
        
        # O Pandas, ao ler HTML, frequentemente deixa espaços e '\n' nas células.
        # Vamos garantir que todo texto seja limpo, mas manteremos o '\n' que pode ter
        # sido capturado para fins de quebra de linha.
        
        for col in tabela_principal.columns:
            # Substitui NaN por string vazia e garante que o valor seja uma string
            tabela_principal[col] = tabela_principal[col].fillna('').astype(str).str.strip()

        # --- ESCRITA NO EXCEL COM FORMATOS BÁSICOS ---

        caminho_completo = os.path.join(os.getcwd(), nome_arquivo)
        writer = pd.ExcelWriter(caminho_completo, engine='xlsxwriter')
        workbook  = writer.book
        worksheet = workbook.add_worksheet('Dados Extraídos') 
        
        # --- DEFINIÇÃO DOS FORMATOS ---
        
        # Formato de Cabeçalho
        header_format = workbook.add_format({
            'bold': True, 'text_wrap': True, 'valign': 'vcenter', 'fg_color': '#696969', 
            'font_color': '#FFFFFF', 'border': 1, 'align': 'center'
        })
        # Formato para Centralizar Texto (Coluna A e outras menores)
        data_center_format = workbook.add_format({'align': 'center', 'valign': 'vcenter'})
        # Formato para Quebra de Texto e Top-Alignment (Colunas B, C, etc.)
        wrap_format = workbook.add_format({'text_wrap': True, 'valign': 'top'})

        # --- ESCREVER CABEÇALHO E APLICAR LARGURAS ---
        
        col_headers = tabela_principal.columns.tolist()
        
        larguras_pixels = {
            0: 45,  # Coluna A
            1: 500, # Coluna B (Representativos)
            2: 1000,# Coluna C (Tese/Questão Jurídica)
            3: 220, # Coluna D
            4: 175, # Coluna E
            5: 265  # Coluna F
        }
        
        for col_num, header in enumerate(col_headers):
            worksheet.write(0, col_num, header, header_format)
            
            # Aplicar Largura
            largura_px = larguras_pixels.get(col_num, 150)
            largura_excel = largura_px / 7
            worksheet.set_column(col_num, col_num, largura_excel)

        # --- ESCREVER DADOS ---
        
        for row_num, row_data in tabela_principal.iterrows():
            excel_row = row_num + 1 
            
            for col_num, header in enumerate(col_headers):
                valor = row_data[header]
                formato_celula = None

                # Colunas B (1) e C (2) são as mais longas e precisam de quebra de texto
                if col_num in [1, 2]:
                    formato_celula = wrap_format
                
                # Coluna A (0) e as colunas finais (3, 4, 5...) devem ser centralizadas
                elif col_num == 0 or col_num > 2:
                    formato_celula = data_center_format

                # Escreve o valor como string (o xlsxwriter/Pandas cuida do resto)
                # O formato `wrap_format` garantirá que o '\n' (se existir) quebre a linha no Excel.
                worksheet.write(excel_row, col_num, str(valor), formato_celula)

        # Fecha o objeto ExcelWriter
        writer.close()
        
        print(f"\n✅ Extração e Formatação Simples concluídas com sucesso.")
        print(f"   -> Todos os hiperlinks foram removidos, e o foco é no texto limpo.")
        print(f"   -> As colunas B e C foram configuradas para quebra de texto e alinhamento superior.")
        print(f"Tabela salva em: {caminho_completo}")

    except requests.exceptions.HTTPError as e:
        print(f"❌ Erro HTTP ao acessar a página: {e}")
    except Exception as e:
        print(f"❌ Ocorreu um erro durante a extração: {e}")
        print(f"Detalhe: {e}")

if __name__ == "__main__":
    extrair_tabela_web_simples()
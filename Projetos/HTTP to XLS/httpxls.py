import pandas as pd
import requests
import os
from io import StringIO # <-- 1. Importar StringIO

def extrair_tabela_web_interativo():
    """
    Pede ao usuário a URL e o nome do arquivo de saída, extrai a tabela
    principal do HTML e salva-a na pasta raiz do script.
    """
    
    # 1. Obter a URL e o nome do arquivo do usuário
    url = input("Por favor, digite o link (URL) da página da web que contém a tabela: ").strip()
    
    if not url.startswith('http'):
        print("❌ URL inválida. O link deve começar com 'http' ou 'https'.")
        return

    nome_arquivo = input("Por favor, digite o nome do arquivo de saída (ex: dados.xlsx): ").strip()
    
    if not nome_arquivo.lower().endswith('.xlsx'):
        nome_arquivo = f"{nome_arquivo.split('.')[0]}.xlsx"
        
    print(f"\nIniciando a extração da tabela da URL: {url}")
    
    try:
        # 2. Obter o conteúdo HTML da página
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        # 3. Usar pandas.read_html para analisar o HTML e encontrar tabelas
        # CORREÇÃO: Passar o HTML para StringIO antes de pd.read_html para evitar o FutureWarning
        tabelas = pd.read_html(StringIO(response.text), header=0) 
        
        if not tabelas:
            print("❌ Nenhuma tabela HTML encontrada na página.")
            return

        # 4. Selecionar a tabela principal (a maior em termos de células)
        tabela_principal = max(tabelas, key=lambda df: df.size)

        # 5. Salvar no Excel na pasta raiz do script (os.getcwd())
        caminho_completo = os.path.join(os.getcwd(), nome_arquivo)
        tabela_principal.to_excel(caminho_completo, index=False)
        
        print(f"\n✅ Extração concluída com sucesso!")
        print(f"Tabela salva em: {caminho_completo}")
        print(f"Dimensões da tabela salva: {tabela_principal.shape[0]} linhas x {tabela_principal.shape[1]} colunas.")

    except requests.exceptions.HTTPError as e:
        print(f"❌ Erro HTTP ao acessar a página: {e}")
    except Exception as e:
        print(f"❌ Ocorreu um erro durante a extração: {e}")
        print("A estrutura da tabela pode ser complexa. Verifique se a URL está correta ou se a tabela requer JavaScript para carregar.")

if __name__ == "__main__":
    extrair_tabela_web_interativo()
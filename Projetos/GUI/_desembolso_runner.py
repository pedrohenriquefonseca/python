"""
Runner isolado para a Curva de Desembolso.
Executado como subprocesso pelo portal para abrir o gráfico em janela do matplotlib.
Importa a função do script original — sem duplicação de lógica.
Uso: python _desembolso_runner.py <caminho_xlsx> <nome_projeto> <dia_corte>
"""
import sys
import os

# Importa do script original
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'Curva de Desembolso'))
from Desembolso import plotar_desembolso

if __name__ == '__main__':
    arquivo     = sys.argv[1]
    nome_projeto = sys.argv[2]
    dia_corte    = int(sys.argv[3])
    plotar_desembolso(arquivo, nome_projeto, dia_corte)

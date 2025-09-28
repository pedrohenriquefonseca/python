#Este programa recebe uma lista de pessoas e sorteia aleatoriamene um dos nomes.
from random import choice

lista = input('Informe 4 nomes separados por vírgula, sem espaço: ').split(',')
final=[]
for nome in lista:
    final.append(nome.strip())
print(final)
print(choice(final))
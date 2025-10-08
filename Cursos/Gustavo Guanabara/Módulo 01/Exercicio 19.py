#Este programa recebe uma lista de pessoas e sorteia aleatoriamene um dos nomes.
import random
lista = input('Informe 4 nomes separados por vírgula, sem espaço: ').split(',')
final=[]
for nome in lista:
    final.append(nome.strip())
    
print(random.choice(final))
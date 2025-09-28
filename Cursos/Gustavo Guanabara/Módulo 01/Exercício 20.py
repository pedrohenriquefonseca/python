#Este programa recebe do usuário uma lista de nomes e a ordena aleatóriamente
from random import shuffle

nomes = input('Digite os nomes a serem sorteados separados por virgula: ').split(',')
lista = [nome.strip() for nome in nomes]
shuffle(lista)
print(lista)
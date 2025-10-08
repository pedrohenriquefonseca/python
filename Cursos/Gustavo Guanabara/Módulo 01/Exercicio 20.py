#Este programa recebe do usuário uma lista de nomes e a ordena aleatóriamente
import random

nomes = input('Digite os nomes a serem sorteados separados por virgula: ').split(',')
lista = [nome.strip() for nome in nomes]

random.shuffle(lista)

print(lista)
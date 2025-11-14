import time
import random

#Pedra, papel e tesoura
print('''Vamos jogar Pedra, Papel e Tesoura! Suas Opções são:
[0] PEDRA
[1] PAPEL
[2] TESOURA''')
usuario = int(input('Qual sua opção? '))
computador = random.randint(0,2)
itens = ('Pedra', 'Papel', 'Tesoura')

print()
print('Pedra')
time.sleep(1)
print('Papel')
time.sleep(1)
print('Tesoura!!')
time.sleep(1)

print()
print('=-'*15)
print(f'O computador escolheu {itens[computador]}')
print(f'O jogador escolheu {itens[usuario]}')
print('=-'*15)

if computador == 0: #pedra
    if usuario == 0:
        print('Deu EMPATE!')
    elif usuario == 1:
        print('O JOGADOR GANHOU!')
    elif usuario == 2:
        print('O COMPUTADOR GANHOU!')
elif computador == 1: #papel
    if usuario == 0:
        print('O COMPUTADOR GANHOU!')
    elif usuario == 1:
        print('Deu EMPATE!')
    elif usuario == 2:
        print('O JOGADOR GANHOU!')
elif computador == 2: #tesoura
    if usuario == 0:
        print('O JOGADOR GANHOU!')
    elif usuario == 1:
        print('O COMPUTADOR GANHOU!')
    elif usuario == 2:
        print('Deu EMPATE!')
print()

# O computador escolhe um numero aleatório entre 0 e 5 e o usuário tenta advinhá-lo
import random
import time

numero: int = random.randint(0,5)
print('Este é um jogo de advinhação. Eu escolhi um numero entre 0 e 5.')
palpite: int = int(input('Qual número eu escolhi: '))
print('Processando...')
time.sleep(2)
print(f'Eu também escolhi {numero}, você ganhou!!!' if numero == palpite else f'Eu escolhi o numero {numero}, você perdeu. Tente denovo!!')
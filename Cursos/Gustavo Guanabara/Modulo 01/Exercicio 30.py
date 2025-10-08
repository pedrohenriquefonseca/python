# O programa indica se o numero digitado pelo usuário é par ou ímpar.

numero = int(input('Digite um número qualquer: '))
print(f'O seu número é PAR.' if numero % 2 == 0 else f'O seu número é ÍMPAR')
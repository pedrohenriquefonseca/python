#O programa recebe um numero de um usuário e retorna qual unidade, dezena, centena e milhar daquele numero

numero = float(input('\nInforme o número desejado: '))
numero = round(numero)

u = numero % 10 
d = numero // 10 % 10
c = numero // 100 % 10
m = numero // 1000 % 10

print(f'A unidade do número indicado é: {u}')
print(f'A dezena do número indicado é: {d}')
print(f'A centena do número indicado é: {c}')
print(f'O milhar do número indicado é: {m}\n')
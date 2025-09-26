#O aplicativo deverá exibir a porção inteira de um numero com casas decimais digitados pelo usuário
import math

numero = float(input('Digite o numero desejado: '))
print(f'A porção inteira do numero {numero} é igual a {math.floor(numero)}')
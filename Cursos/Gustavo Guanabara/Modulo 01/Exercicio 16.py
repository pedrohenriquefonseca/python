#O script deverá exibir a porção inteira de um numero com casas decimais digitados pelo usuário

#Alternativa 01
#import math
#numero = float(input('Digite o numero desejado: '))
#print(f'A porção inteira do numero {numero} é igual a {math.floor(numero)}')

#Alternativa 02
import math
numero = float(input('Digite o numero desejado: '))
print(f'A porção inteira do numero {numero} é igual a {math.floor(numero)}, e a porção fracionada é igual a {numero - math.floor(numero):.4f}')
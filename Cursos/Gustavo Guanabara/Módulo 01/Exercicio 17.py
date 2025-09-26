# O script calcula a dimensão da hipotenusa de um triangulo retângulo a partir da dimensão dos seus catetos

#Alternativa 01
# oposto = float(input('Digite a dimensão do cateto oposto do triangulo: '))
# adjacente = float(input('Agora digite a dimensão do cateto adjacente do triângulo: '))
# print(f'O valor da hipotenusa do seu triângulo é {(oposto ** 2 + adjacente ** 2) ** 0.5:.2f}')

#Alternativa 02
import math
oposto = float(input('Digite a dimensão do cateto oposto do triangulo: '))
adjacente = float(input('Agora digite a dimensão do cateto adjacente do triângulo: '))
print(f'O valor da hipotenusa do seu triângulo é {math.hypot(oposto , adjacente):.2f}')

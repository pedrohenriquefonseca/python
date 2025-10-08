# O programa calcula seno, cosseno e tangente de um dado angulo
from math import radians, sin, cos, tan

angulo = float(input('Informe o angulo desejado: '))
angulorad = radians(angulo)
print(f'O seno do angulo {angulo} é igual a {sin(angulorad):.2f},')
print(f'O cosseno do angulo {angulo} é igual a {cos(angulorad):.2f},')
print(f'A tangente do angulo {angulo} é igual a {tan(angulorad):.2f}.')
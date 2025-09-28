# O programa calcula seno, cosseno e tangente de um dado angulo
import math

angulo = float(input('Informe o angulo desejado: '))
angulorad = math.radians(angulo)
print(f'O seno do angulo {angulo} é igual a {math.sin(angulorad):.2f},')
print(f'O cosseno do angulo {angulo} é igual a {math.cos(angulorad):.2f},')
print(f'A tangente do angulo {angulo} é igual a {math.tan(angulorad):.2f}.')
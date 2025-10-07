# O programa recebe 3 comprimentos de segmentos e informa ao usuário se eles podem formar um triangulo

n1 = float(input('Informe o valor do primeiro segmento: '))
n2 = float(input('Informe o valor do segundo segmento: '))
n3 = float(input('Informe o valor do terceiro segmento: '))

if n1 < n2 + n3 and n2 < n1 + n3 and n3 < n1 + n2:
    print(f'Yay! Os segmentos informados ({n1}, {n2} e {n3}) PODEM formar um triângulo.')
else:
    print(f'Nay, os segmentos informados ({n1}, {n2} e {n3}) NÃO PODEM formar um triângulo.')
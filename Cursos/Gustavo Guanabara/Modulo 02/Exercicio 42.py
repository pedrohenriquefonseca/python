print('=-' * 30)
a = int(input('Digite o tamanho do primeiro segmento: '))
b = int(input('Digite o tamanho do segundo segmento: '))
c = int(input('Digite o tamanho do terceiro segmento:'))

if a < b + c and b < a + c and c < b + a:
    print(f'\nOs segmentos de comprimento {a}, {b} e {c} podem formar um triângulo.')
else:
    print(f'\nOs segmentos de comprimento {a}, {b} e {c} NÃO podem formar um triângulo.')
    print('=-' * 30)
    exit()

if a == b == c:
    print('O seu triângulo será um triângulo EQUILÁTERO')
elif a == b != c or b == c != a or c == a != b:
    print('O seu triângulo será um triângulo ISÓSCELES.')
else:
    print('O seu triângulo será um triângulo ESCALENO')

print('=-' * 30)

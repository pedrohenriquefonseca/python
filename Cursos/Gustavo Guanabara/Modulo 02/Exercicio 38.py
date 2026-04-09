primeiro = int(input('Informe o primeiro número: '))
segundo = int(input('Informe o segundo número:  '))

if primeiro > segundo:
    print(f'{primeiro} é MAIOR que {segundo}.')
elif primeiro < segundo:
    print(f'{primeiro} é MENOR que {segundo}.')
else:
    print(f'{primeiro} é IGUAL ao {segundo}.')
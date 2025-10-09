numero = int(input('Digite o número desejado: '))
print('Escolha uma das bases para conversão:')
print('[1] - Converter para BINÁRIO')
print('[2] - Converter para OCTAL')
print('[3] - Converter para HEXADECIMAL')

while True:
    opcao = int(input('Digite a sua opção: '))
    if opcao == 1:
        print(f'O número informado convertido para BINÁRIO é {bin(numero)}.')
    elif opcao == 2:
        print(f'O número informado convertido para OCTAL é {oct(numero)}.')
    elif opcao == 3:
        print(f'O número informado convertido para HEXADECIMAL é {hex(numero)}.')
    else:
        sair = input('Opção inválida! Pressione S para sair ou Enter para tentar novamente: ')
        if sair.strip().lower() == 's':
            print('Saindo do programa...')
            break
    
# O programa recebe o salário do usuário e calcula o aumento de acordo com faixas de valor.

while True:
    salario = float(input('\nInforme o seu salário atual: R$'))

    if salario >= 1250:
        print(f'O novo valor do seu salário será de R${salario * 1.1:.2f}.')
    else:
        print(f'O novo valor do seu salário será de R${salario * 1.15:.2f}.')
    
    sair = str(input('\nPressione S para sair ou Enter para continuar: '))
    if sair.lower() == 's':
        break
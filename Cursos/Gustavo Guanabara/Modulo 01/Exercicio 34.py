# O programa recebe o salário do usuário e calcula o aumento de acordo com faixas de valor.

print('-=' * 20)
print('Calculadora de Aumento de Salário')
print('-=' * 20)

while True:
    salario = float(input('Informe o seu salário atual: R$'))
    if salario >= 1250:
        print(f'O novo valor do seu salário será de R${salario * 1.1:.2f}.')
    else:
        print(f'O novo valor do seu salário será de R${salario * 1.15:.2f}.')
    
    sair = str(input('Pressione S para sair ou Enter para continuar: '))
    if sair.lower() == 's':
        break
casa = float(input('\nInforme o valor da casa: R$ '))
salario = float(input('Informe o valor do seu salário: R$ '))
duracao = int(input('Informe em quantos anos você pretende quitar o financiamento: '))

prestacao_mensal = casa / (duracao * 12)

if prestacao_mensal > salario * 0.3:
    print(f'Para comprar uma casa de R$ {casa}, a prestação mensal seria de R$ {prestacao_mensal:.2f} - FINANCIAMENTO RECUSADO.\n')
else:
    print(f'Para comprar uma casa de R$ {casa}, a prestação mensal seria de R$ {prestacao_mensal:.2f} - FINANCIAMENTO AUTORIZADO.\n')


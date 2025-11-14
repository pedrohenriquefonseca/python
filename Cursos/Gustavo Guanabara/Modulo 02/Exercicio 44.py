#Simulador de Lojas
print('='*20,' SIMULADOR DE LOJAS ', '='*20)
valor = float(input('Preço das Compras: R$ '))
print('''FORMA DE PAGAMENTO
[1] - à vista no dinheiro ou cheque'
[2] - à vista no cartão')
[3] - 2x no cartão'
[4] - 3x ou mais no cartão''')
opcao = int(input('Qual é a sua opção entre 1 e 4? '))

while opcao not in [1, 2, 3, 4]:
    opcao = int(input('Digite uma forma de pagamento válida (entre 1 e 4): '))

if opcao == 1 or opcao == 2:
    parcelas = 1
elif opcao == 3:
    parcelas = 2
elif opcao == 4:
    parcelas = int(input('Em quantas parcelas você deseja pagar? '))
    
if opcao == 1:
    print(f'Você recebeu um desconto de 10% sobre sua compra. O valor final a ser pago será de R$ {valor * 0.9:.2f}.')
elif opcao == 2:
    print(f'Voce recebeu um desconto de 5% sobre sua compra. O valor final a ser pago será de R$ {valor * 0.95:.2f}.')
elif opcao == 3: 
    print(f'Sua compra de R${valor:.2f} será parcelada no cartão em 2x sem juros. O valor de cada parcela será de R$ {valor * 0.5:.2f}.')
else:
    print(f'Sua compra no valor de R$ {valor:.2f} será parcelada em {parcelas} vezes no cartão, com um juros de 20%.')
    print(f'O valor total da compra será de R$ {valor * 1.2:.2f}, e o valor de cada parcela será de R$ {valor * 1.2 / parcelas:.2f}.')

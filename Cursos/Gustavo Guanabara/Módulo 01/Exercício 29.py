# O programa le a velocidade atual de um carro e, caso ela seja superior a tal limite, calcula qual o valor da multa devida

velocidade = int(input('Digite a sua atual velocidade: '))
if velocidade > 80:
    multa = (velocidade - 80) * 7
    print(f'Você está acima do limite de velocidade da via, tome uma multa no valor de R$ {multa:.2f}')
else:
    print('Vai na paz irmão.')
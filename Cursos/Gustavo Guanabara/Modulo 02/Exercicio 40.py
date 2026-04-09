n1 = float(input('Informe sua primeira nota: '))
n2 = float(input('Informe a sua segunda nota: '))

media = (n1 + n2) / 2

print(f'Sua média final foi de {media:.2f} pontos.')
if media <= 5:
    print('Você está REPROVADO.')
elif media >= 7:
    print('Você está APROVADO.')
else:
    print('Você está em RECUPERAÇÃO.')
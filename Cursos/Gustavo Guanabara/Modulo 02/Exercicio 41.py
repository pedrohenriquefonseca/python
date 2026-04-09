idade = int(input('Informe a idade do atleta: '))

if idade <= 9:
    print('Trata-se de um atleta MIRIM.')
elif idade <= 14:
    print('Trata-se de um atleta INFANTIL.')
elif idade <= 19:
    print('Trata-se de um atleta JUNIOR.')
elif idade <= 25:
    print('Trata-se de um atleta SÊNIOR.')
else:
    print('Trata-se de um atleta MASTER.')

from datetime import datetime

nascimento = int(input('Qual seu ano de nascimento? '))
idade = datetime.now().year - nascimento
alistamento = nascimento + 18
hoje = datetime.now().year

print(f'Quem nasceu em {nascimento} tem {idade} anos em {hoje}.')
if idade < 18:
    print(f'Ainda faltam {18 - idade} anos para o seu alistamento.')
    print(f'Seu alistamento será em {alistamento}.')
elif idade > 18:
    print(f'Você deveria ter se alistado há {hoje - alistamento} anos.')
    print(f'Seu alistamento foi em {alistamento}.')
else:
    print('Está na hora de servir ao exército, aliste-se AGORA!')

#O programa recebe a cidade de nascimento do usuário e confere se o nome da cidade começa com a palavra santo

cidade = str(input('Qual sua cidade de nascimento? ')).strip()
lista = cidade.split()
print('True') if lista[0].lower() == 'santo' else print('False')


#O programa recebe um nome do usuário e apresenta uma análise sobre a string

nome = input('Digite o nome a ser analisado: ').strip()
fatiado = nome.split()
sem = nome.replace(' ','')

print(f'O seu nome em maiúsculas é: {nome.upper()}')
print(f'O seu nome em minúsculas é: {nome.lower()}')
print(f'O seu nome tem ao todo {len(sem)} caracteres.')
print(f'Seu primeiro nome é {fatiado[0]} e ele tem {len(fatiado[0])} letras')

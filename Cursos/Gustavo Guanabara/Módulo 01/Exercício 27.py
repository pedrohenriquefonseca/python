#O programa recebe o nome do usuário e indica qual é seu primeiro e ultimo nome

nome=str(input('Digite o nome completo a ser analisado: ')).lower().strip()
lista = nome.split()
print(f'Seu primeiro nome é {lista[0].title()}, e seu ultimo nome é {lista[-1].title()}.')

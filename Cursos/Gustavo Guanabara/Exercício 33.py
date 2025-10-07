# O programa recebe 3 valores do usuário e indica qual é o menor e qual é o maior valor.

primeiro = int(input('Digite o primeiro valor: '))
segundo = int(input('Digite o segundo valor: '))
terceiro = int(input('Digite o terceiro valor: '))

lista = [primeiro, segundo, terceiro]

print(f'\nO maior valor digitado é {max(lista)}.')
print(f'O menor valor digitado é {min(lista)}.')
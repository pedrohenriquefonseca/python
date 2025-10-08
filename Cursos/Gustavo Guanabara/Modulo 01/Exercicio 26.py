# O programa recebe uma frase e indica quantas vezes e qual posição a letra A aparece nela.

frase = str(input('Digite a frase que deseja ser analisada: ')).lower().strip()

print(f'A letra A aparece {frase.lower().count("a")} vezes.')
print(f'A primeira letra A apareceu na posição {frase.find("a")+1}')
print(f'A ultima letra A apareceu na posição {frase.rfind("a")+1}')
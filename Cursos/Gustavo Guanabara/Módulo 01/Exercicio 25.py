#O programa verifica se existe a palavra Silva no nome completo recebido do usuário

nome = str(input('Digite seu nome completo: ')).strip()
print('Seu nome tem Silva') if 'silva' in nome.lower().split() else print('Seu nome não tem Silva')

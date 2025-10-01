#Calcula o preço da passagem baseado em faixas de distancia entre as duas cidades

distancia = int(input('Qual é a distância da sua viagem, em quilometros? '))
print(f'Sua viagem custará R$ {distancia * 0.45:.2f}.' if distancia >= 200 else f'Sua viagem custará R$ {distancia * 0.50:.2f}.')
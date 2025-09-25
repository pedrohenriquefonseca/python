#Captando as informações
preço = float(input('Qual o valor atual do produto que deseja comprar? '))
desconto = float(input('Qual o desconto, em porcentagem, a ser aplicado na compra? '))

#Apresentando as informações calculadas
print (f'O preço do produto com {desconto}% de desconto será de R${round(preço - (preço * (desconto/100)),2)}.')                        
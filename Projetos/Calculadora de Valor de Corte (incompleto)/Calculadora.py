#O programa recebe parâmetros de determinado negócio imobiliário e calcula o maior valor a ser pago em um leilão

#Valores dados
leilao = float(input('Informe o valor do 1o leilão do imóvel: R$ '))
analoga = float(input('Informe o valor de venda da obra análoga ao objeto do leilão: R$ '))

#Calculados
metavenda = analoga - 15000

comissao_porcentagem =  0.05
documentacao_porcentagem = 0.11
obra_porcentagem = 0.12
cc_porcentagem = 0.02
lucro_porcentagem = 0.195 #15% sobre preço de (leilão + comissão + doc + obras + cc)

custo_porcentagem = (comissao_porcentagem + 
    documentacao_porcentagem + 
    obra_porcentagem + 
    cc_porcentagem +
    lucro_porcentagem)

custoinicial = leilao * (1 + comissao_porcentagem + documentacao_porcentagem + obra_porcentagem + lucro_porcentagem)
corteinicial = metavenda - custoinicial + leilao


print(f'\n\nO valor inicial do leilão é de R$ {leilao:,.2f}.')
print(f'Comissão do leiloeiro: R$ {comissao:,.2f}.')
print(f'Custo de Documentação: R$ {documentacao:,.2f}.')
print(f'Custo de obras: R$ {obra:,.2f}.')
print(f'Margem de lucro: R$ {lucro:,.2f}.')
print(f'O preço de corte inicial do negócio é de R$ {corteinicial:,.2f}.')

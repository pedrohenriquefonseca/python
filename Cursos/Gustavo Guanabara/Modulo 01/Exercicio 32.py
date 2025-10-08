# O programa recebe um ano do usuário e indica e ele é ou não bissexto.
from datetime import datetime

ano = int(input(f'Que ano quer consultar, ou 0 para consultar o ano atual: '))

if ano == 0:    
    ano = datetime.now().year

if ano % 4 == 0 and ano % 100 != 0 or ano % 400 == 0:
    print(f'O ano {ano} É BISSEXTO')
else:   
    print(f'O ano {ano} NÃO É BISSEXTO')

#Script para pedir usuário, senha, e conferir com banco de dados existente
import getpass

#Solicitando Usuário e senha
usuario = input ("Digite seu usuário: ")
senha = getpass.getpass("Digite sua senha de 8 dígitos: ")
while len(senha) < 8:
    senha = getpass.getpass("Senha inválida. Digite novamente uma senha de 8 dígitos: ")
else:
    pass

#Salvando usuário e senha no arquivo bd.txt
try:
    # Verificando se o arquivo existe e lendo os dados existentes
    with open("bd.txt", "r") as arquivo:
        linhas = arquivo.readlines()
    
    # Verificando se o par usuário e senha já existe
    usuario_senha_existe = False
    for linha in linhas:
        if linha.strip() == f"{usuario},{senha}":
            usuario_senha_existe = True
            break
    
    # Se o par usuário e senha não existir, adiciona ao arquivo
    if not usuario_senha_existe:
        with open("bd.txt", "a") as arquivo:
            arquivo.write(f"{usuario},{senha}\n")
    
    # Se o arquivo não existir, cria um novo
except FileNotFoundError:
    with open("bd.txt", "w") as arquivo:
        arquivo.write(f"{usuario},{senha}\n")

if usuario_senha_existe == True:
    print("Login realizado com sucesso!")
else:
    print("Usuário ou senha inválidos!")

    
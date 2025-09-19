import getpass
import os

# Obtendo o caminho do diretório onde o script está localizado
diretorio_script = os.path.dirname(os.path.abspath(__file__))
# Construindo o caminho completo para o arquivo bd.txt
caminho_bd = os.path.join(diretorio_script, "bd.txt")

#Solicitando Usuário e senha
usuario = input("Digite seu usuário: ")
senha = getpass.getpass("Digite sua senha de 8 dígitos: ")
while len(senha) < 8:
    senha = getpass.getpass("Senha inválida. Digite novamente uma senha de 8 dígitos: ")

#Verificando usuário e senha no arquivo bd.txt
try:
    # Verificando se o arquivo existe e lendo os dados existentes
    with open(caminho_bd, "r") as arquivo:
        linhas = arquivo.readlines()
    
    # Verificando se o usuário existe e se a senha está correta
    usuario_existe = False
    senha_correta = False
    
    for linha in linhas:
        partes = linha.strip().split(",")
        usuario_bd, senha_bd = partes
            
        if usuario_bd == usuario:
            usuario_existe = True
            if senha_bd == senha:
                senha_correta = True
            break
    
    # Lógica para decidir o que fazer com base nas verificações
    if usuario_existe  and senha_correta:
            print("Login realizado com sucesso!")
    elif usuario_existe:
            print("Senha incorreta para o usuário informado. Acesso negado.")
    else:
        # Usuário não existe, vamos cadastrá-lo
        with open(caminho_bd, "a") as arquivo:
            arquivo.write(f"{usuario},{senha}\n")
        print("Novo usuário cadastrado com sucesso!")

# Se o arquivo não existir, cria um novo
except FileNotFoundError:
    with open(caminho_bd, "w") as arquivo:
        arquivo.write(f"{usuario},{senha}\n")
    print("Arquivo de banco de dados criado. Novo usuário cadastrado!")
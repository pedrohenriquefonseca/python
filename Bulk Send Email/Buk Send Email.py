import smtplib  # Para envio de emails via SMTP
import time     # Para adicionar delays entre envios
from email.mime.text import MIMEText  # Para formatação de mensagens de email
import getpass  # Para entrada segura de senha

gmail_user = str(input('Informe seu endereço de email: '))
gmail_password = str(getpass.getpass('Digite sua senha de 8 dígitos: '))
destinatarios = input('Informe os endereços dos destinatários separados por vírgula: ').split(',')
assunto = str(input('Digite o assunto do email: '))
corpo = str(input('Digite o corpo do email (utilize aspas triplas para linhas multiplas): '))

enviados = 0
try:
    # Conectar ao Gmail
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(gmail_user, gmail_password)
    
    print(f'Enviando para {len(destinatarios)} destinatários...')
    
    for i, email in enumerate(destinatarios, 1):
        try:
            # Criar mensagem
            msg = MIMEText(corpo, 'plain', 'utf-8')
            msg['From'] = gmail_user
            msg['To'] = email
            msg['Subject'] = assunto
            
            # Enviar
            server.send_message(msg)
            enviados += 1
            print(f'{i}/{len(destinatarios)} ✓ {email}')
            time.sleep(1)  # delay padrão de 1 segundo
            
        except Exception as e:
            print(f'{i}/{len(destinatarios)} ✗ {email} - Erro: {e}')
    
    server.quit()
    print(f'\nConcluído! {enviados}/{len(destinatarios)} emails enviados.')
    
except Exception as e:
    print(f'Erro de conexão: {e}')
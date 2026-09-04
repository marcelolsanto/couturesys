import os

# Conteúdo exato que precisamos (baseado no seu teste)
conteudo = """SECRET_KEY=django-insecure-chave-de-teste-12345
DEBUG=True
DB_NAME=couturesys_db
DB_USER=postgres
DB_PASSWORD=Mr#321456
DB_HOST=localhost
DB_PORT=5432
"""

print("1. Removendo arquivo .env antigo...")
try:
    if os.path.exists('.env'):
        os.remove('.env')
        print("   -> Arquivo antigo deletado.")
    else:
        print("   -> Arquivo não existia.")
except Exception as e:
    print(f"   -> Erro ao deletar: {e}")

print("2. Criando novo .env com codificação UTF-8...")
try:
    # O segredo está aqui: encoding='utf-8'
    with open('.env', 'w', encoding='utf-8') as f:
        f.write(conteudo)
    print("   -> Sucesso! Novo arquivo .env criado.")
except Exception as e:
    print(f"   -> Falha ao criar arquivo: {e}")

print("3. Concluído.")
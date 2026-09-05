#!/bin/sh
set -e

echo "🚀 [Docker] Inicializando CoutureSys..."

# Aguarda o banco PostgreSQL ficar pronto para conexões
if [ -n "$DB_HOST" ]; then
    echo "⏳ [Docker] Aguardando PostgreSQL..."
    python << 'EOF'
import socket, time, os, sys

host = os.environ.get('DB_HOST', 'db')
port = int(os.environ.get('DB_PORT', 5432))

for attempt in range(60):
    try:
        with socket.create_connection((host, port), timeout=2):
            print(f"✅ [Docker] PostgreSQL acessível em {host}:{port}!")
            sys.exit(0)
    except Exception:
        time.sleep(1)

print("❌ [Docker] Timeout aguardando PostgreSQL.")
sys.exit(1)
EOF
fi

# Aplica migrações pendentes
echo "📦 [Docker] Aplicando migrações do Django..."
python manage.py migrate --noinput

# Coleta estáticos para que o WhiteNoise / Gunicorn possa servi-los
echo "🎨 [Docker] Coletando arquivos estáticos..."
python manage.py collectstatic --noinput

echo "✨ [Docker] Pronto para atender requisições!"

# Executa comando final
exec "$@"

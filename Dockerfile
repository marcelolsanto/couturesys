# ==============================================================================
# Dockerfile — CoutureSys
# ==============================================================================
FROM python:3.12-slim

# Otimizações de execução do Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dependências do sistema para compilação, PostgreSQL e geração de PDF (Cairo)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    libcairo2-dev \
    pkg-config \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Instalação das dependências Python com cache de camadas
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Script de entrada para espera de banco e migrações
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Copia o restante do código-fonte do projeto
COPY . /app/

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]

# Comando padrão em produção utilizando Gunicorn
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120"]
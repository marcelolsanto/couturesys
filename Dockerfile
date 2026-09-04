# Usa uma imagem oficial e enxuta do Python 3.12
FROM python:3.12-slim

# Define variáveis de ambiente para otimizar o Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Define o diretório de trabalho dentro do contêiner
WORKDIR /app

# Instala as dependências do sistema necessárias para o Cairo (geração de PDF) e PostgreSQL
# O 'rm -rf' no final limpa o cache do apt para manter a imagem com baixo consumo de RAM
RUN apt-get update && apt-get install -y \
    pkg-config \
    libcairo2-dev \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copia os requisitos e instala as dependências do Python
COPY requirements.txt /app/
RUN pip install --no-cache-dir --default-timeout=1000 -r requirements.txt

# Copia todo o código do projeto para o contêiner
COPY . /app/

# Expõe a porta que o Django vai rodar
EXPOSE 8000

# Comando padrão para iniciar o servidor
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
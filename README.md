# 🧵 CoutureSys

Sistema de gestão completo para ateliê de alta costura, desenvolvido com **Django** e **PostgreSQL**. Cobre todo o ciclo de vida de um pedido — do orçamento ao contrato assinado — com automação financeira, controle de estoque e integração com IAs generativas.

## ✨ Funcionalidades

- **Gestão de Pedidos** com pipeline de status: Orçamento → Aprovado → Compras → Confecção → Provas → Entregue
- **Precificação Inteligente**: fórmula contábil com custo/hora, rateio fixo, impostos e margem de lucro configuráveis
- **Fichas Técnicas**: materiais, medidas por template JSON, croqui da peça
- **Controle de Estoque**: entradas e saídas de materiais com auditoria
- **Módulo Jurídico**: geração de contratos em PDF com variáveis dinâmicas
- **Automação Financeira**: ao assinar um contrato, Contas a Receber e Pagar são geradas automaticamente via Django Signals
- **Dashboard Financeiro**: DRE operacional e fluxo de caixa real
- **Simulador de Pagamento**: análise de viabilidade por pedido com exportação em PDF
- **Integração com IA**:
  - [Google Gemini](https://ai.google.dev/): interpreta pedidos em linguagem natural e gera a ficha técnica
  - [OpenAI DALL-E](https://openai.com/dall-e-3): gera o croqui da peça a partir da descrição
- **Auditoria** com `django-simple-history`
- **Docker** pronto para desenvolvimento e deploy

---

## 🗂️ Estrutura do Projeto

```
couturesys/
├── config/          # Configurações Django (settings, urls, wsgi)
├── core/            # App de Clientes
├── producao/        # App de Pedidos, Fichas Técnicas, Estoque, IA
├── financeiro/      # App Financeiro (Dashboard, Contas, Simulador)
├── juridico/        # App de Contratos
├── static/          # Arquivos estáticos (JS)
├── Dockerfile       # Receita de construção da imagem do container
├── docker-compose.yml # Orquestração do app + PostgreSQL
├── .dockerignore    # Arquivos ignorados no build da imagem
├── entrypoint.sh    # Script de inicialização (espera DB + migrações)
├── requirements.txt # Dependências Python
└── .env.example     # Template de variáveis de ambiente
```

---

## 🚀 Instalação e Execução

### Pré-requisitos
- Python 3.10+
- PostgreSQL 13+ **ou** Docker

### Opção 1 — Com Docker (Recomendado)

```bash
# 1. Clone o repositório
git clone https://github.com/seu-usuario/couturesys.git
cd couturesys

# 2. Configure as variáveis de ambiente
cp .env.example .env
# Edite o .env com seus valores

# 3. Suba os containers
docker-compose up --build
```

A aplicação estará disponível em `http://localhost:8001`.

---

### Opção 2 — Local (sem Docker)

```bash
# 1. Clone e entre no diretório
git clone https://github.com/seu-usuario/couturesys.git
cd couturesys

# 2. Crie e ative o ambiente virtual
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Configure as variáveis de ambiente
cp .env.example .env
# Edite o .env com os dados do seu banco PostgreSQL local

# 5. Rode as migrations
python manage.py migrate

# 6. (Opcional) Popule dados de exemplo
python seed_data.py

# 7. Crie o superusuário
python manage.py createsuperuser

# 8. Inicie o servidor
python manage.py runserver
```

A aplicação estará disponível em `http://localhost:8000`.

---

## ⚙️ Variáveis de Ambiente

Copie `.env.example` para `.env` e preencha:

| Variável | Descrição | Obrigatório |
|----------|-----------|-------------|
| `SECRET_KEY` | Chave secreta do Django | ✅ |
| `DEBUG` | `True` (dev) ou `False` (prod) | ✅ |
| `ALLOWED_HOSTS` | Hosts permitidos, separados por vírgula | ✅ |
| `DB_NAME` | Nome do banco PostgreSQL | ✅ |
| `DB_USER` | Usuário do banco | ✅ |
| `DB_PASSWORD` | Senha do banco | ✅ |
| `DB_HOST` | Host do banco (`localhost` ou `db` no Docker) | ✅ |
| `DB_PORT` | Porta do banco (padrão: `5432`) | ✅ |
| `GEMINI_API_KEY` | Chave da API Google Gemini (IA) | ⚪ Opcional |
| `OPENAI_API_KEY` | Chave da API OpenAI/DALL-E (Croquis) | ⚪ Opcional |

> **Nota:** As funcionalidades de IA são opcionais. Se as chaves não estiverem configuradas, o sistema opera normalmente com fallback manual.

---

## 🛠️ Stack Tecnológica

| Tecnologia | Uso |
|-----------|-----|
| Python 3.10+ | Linguagem principal |
| Django 5.x | Framework web |
| PostgreSQL | Banco de dados relacional |
| Docker + Docker Compose | Containerização |
| `django-simple-history` | Auditoria de modelos |
| `python-decouple` | Gestão de variáveis de ambiente |
| `xhtml2pdf` | Geração de PDFs |
| `google-generativeai` | Integração com Google Gemini |
| `openai` | Integração com DALL-E |

---

## 🔐 Segurança

- Credenciais e chaves secretas são gerenciadas exclusivamente via `.env` (nunca commitadas)
- `SECRET_KEY` e senhas do banco nunca estão hardcoded no código
- `ALLOWED_HOSTS` configurável por ambiente
- `DEBUG=False` em produção
- Atualizações de estoque usam `F()` expressions para operações atômicas no banco

---

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.

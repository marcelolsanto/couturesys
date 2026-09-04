import json
import os
import requests
import google.generativeai as genai
from django.conf import settings
from django.core.files.base import ContentFile
from openai import OpenAI

# Tenta configurar o Gemini
chave_gemini = os.getenv("GEMINI_API_KEY")
if chave_gemini:
    genai.configure(api_key=chave_gemini)


def interpretar_pedido_cliente(texto_cliente):
    """
    Usa o Google Gemini 2.0 Flash (Modelo disponível na sua conta).
    """
    print(f"🤖 Gemini lendo: '{texto_cliente[:30]}...'")

    if not chave_gemini:
        print("❌ Erro: Chave GEMINI_API_KEY não encontrada no .env")
        return _dados_fallback(texto_cliente)

    # Configuração
    generation_config = {
        "temperature": 0.7,
        "response_mime_type": "application/json",
    }

    # ATUALIZAÇÃO: Usando o modelo que apareceu na sua lista
    model = genai.GenerativeModel("gemini-2.0-flash", generation_config=generation_config)

    prompt_sistema = """
    Você é uma Estilista Virtual.
    Analise o pedido e retorne APENAS um JSON válido.

    Estrutura obrigatória do JSON:
    {
        "resumo_peca": "Título curto",
        "descricao_visual": "Descrição técnica detalhada...",
        "horas_estimadas": 15.5,
        "materiais_sugeridos": ["Material A", "Material B"],
        "prompt_imagem": "Fashion sketch description in english"
    }
    """

    try:
        response = model.generate_content(f"{prompt_sistema}\n\nPedido: {texto_cliente}")
        return json.loads(response.text)

    except Exception as e:
        print(f"❌ Erro no Gemini: {e}")
        # Se der erro de novo, lista os modelos para debug
        if "404" in str(e):
            try:
                print("🔍 Modelos disponíveis na sua conta:")
                for m in genai.list_models():
                    if 'generateContent' in m.supported_generation_methods:
                        print(f" - {m.name}")
            except:
                pass

        return _dados_fallback(texto_cliente)


def _dados_fallback(texto):
    return {
        "resumo_peca": "Pedido Manual (Erro IA)",
        "descricao_visual": f"Não foi possível processar: {texto}",
        "horas_estimadas": 5.0,
        "materiais_sugeridos": ["Verificar manualmente"],
        "prompt_imagem": "fashion sketch"
    }


def gerar_croqui_dalle(prompt_imagem):
    api_key = getattr(settings, 'OPENAI_API_KEY', None)

    # Verifica se a chave existe e parece válida (maior que 10 caracteres)
    if not api_key or len(str(api_key)) < 10:
        print("⚠️ Chave OpenAI não configurada ou inválida. Gerando croqui simulado.")
        return _baixar_imagem_simulada(prompt_imagem)

    try:
        print("🎨 Tentando gerar croqui com DALL-E...")
        client = OpenAI(api_key=api_key)
        response = client.images.generate(
            model="dall-e-3",
            prompt=f"Fashion sketch, white background, {prompt_imagem}",
            size="1024x1024",
            quality="standard",
            n=1,
        )
        return _download_imagem(response.data[0].url)

    except Exception as e:
        print(f"⚠️ DALL-E falhou ({e}). Usando croqui simulado.")
        return _baixar_imagem_simulada(prompt_imagem)


def _baixar_imagem_simulada(descricao):
    palavra = descricao.split(" ")[0] if descricao else "Croqui"
    url = f"https://placehold.co/800x800/EEE/31343C/png?text=Croqui:+{palavra}&font=playfair-display"
    return _download_imagem(url, prefixo="croqui_simulado")


def _download_imagem(url, prefixo="croqui_ia"):
    try:
        img_response = requests.get(url)
        if img_response.status_code == 200:
            file_name = f"{prefixo}_{os.urandom(4).hex()}.png"
            return ContentFile(img_response.content, name=file_name)
    except:
        return None
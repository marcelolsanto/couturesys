import urllib.parse


def gerar_link_whatsapp(telefone, mensagem):
    """
    Recebe um telefone (com ou sem formatação) e uma mensagem texto.
    Retorna a URL completa para abrir no WhatsApp.
    """
    if not telefone:
        return None

    # 1. Limpa tudo que não for número
    numeros = ''.join(filter(str.isdigit, telefone))

    # 2. Validação básica (tem que ter DDD + Numero = 10 ou 11 dígitos)
    if len(numeros) < 10:
        return None

    # 3. Adiciona código do país (Brasil = 55) se não tiver
    if not numeros.startswith('55'):
        numeros = f"55{numeros}"

    # 4. Codifica a mensagem para URL (troca espaço por %20, etc)
    mensagem_codificada = urllib.parse.quote(mensagem)

    return f"https://wa.me/{numeros}?text={mensagem_codificada}"
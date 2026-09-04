import os

# Configurações
DIRETORIO_RAIZ = '.'
ARQUIVO_SAIDA = 'raio_x_projeto.txt'
IGNORE_DIRS = {'.venv', 'venv', '.git', '__pycache__', 'migrations', '.idea'}
EXTENSOES_ACEITAS = {'.py', '.html', '.css', '.js'}


def gerar_raio_x():
    with open(ARQUIVO_SAIDA, 'w', encoding='utf-8') as saida:
        saida.write("=== RAIO-X DO PROJETO COUTURESYS ===\n\n")

        # 1. Estrutura de Pastas
        saida.write("--- ESTRUTURA DE DIRETÓRIOS ---\n")
        for root, dirs, files in os.walk(DIRETORIO_RAIZ):
            # Remove pastas ignoradas para não entrar nelas
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
            level = root.replace(DIRETORIO_RAIZ, '').count(os.sep)
            indent = ' ' * 4 * (level)
            saida.write(f"{indent}{os.path.basename(root)}/\n")
            subindent = ' ' * 4 * (level + 1)
            for f in files:
                saida.write(f"{subindent}{f}\n")

        saida.write("\n" + "=" * 50 + "\n\n")

        # 2. Conteúdo dos Arquivos
        saida.write("--- CONTEÚDO DOS ARQUIVOS ---\n")
        for root, dirs, files in os.walk(DIRETORIO_RAIZ):
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]

            for file in files:
                if any(file.endswith(ext) for ext in EXTENSOES_ACEITAS):
                    caminho_completo = os.path.join(root, file)

                    saida.write(f"\n{'=' * 20} ARQUIVO: {caminho_completo} {'=' * 20}\n")

                    try:
                        with open(caminho_completo, 'r', encoding='utf-8') as f:
                            conteudo = f.read()
                            saida.write(conteudo)
                    except Exception as e:
                        saida.write(f"[Erro ao ler arquivo: {e}]")

                    saida.write("\n")

    print(f"✅ Raio-X gerado com sucesso em: {ARQUIVO_SAIDA}")


if __name__ == '__main__':
    gerar_raio_x()
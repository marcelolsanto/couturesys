from django.core.management.base import BaseCommand
from producao.models import Pedido, FichaTecnica, TemplateMedida
from core.models import Cliente
from producao.ai_service import interpretar_pedido_cliente, gerar_croqui_dalle
from django.utils import timezone
from decimal import Decimal

class Command(BaseCommand):
    help = 'Simula o atendimento de IA via WhatsApp'

    def handle(self, *args, **kwargs):
        self.stdout.write("🤖 IA: Olá! Sou a Estilista Virtual. Descreva a roupa que o cliente quer:")
        texto_cliente = input(">> ") # Você digita aqui como se fosse o cliente

        self.stdout.write("⏳ IA: Processando pedido... desenhando croqui... (Aguarde)")

        # 1. Chama a Inteligência Artificial
        try:
            dados_ia = interpretar_pedido_cliente(texto_cliente)
            imagem_croqui = gerar_croqui_dalle(dados_ia['prompt_imagem'])
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Erro na API da OpenAI: {e}"))
            return

        # 2. Busca ou Cria um Cliente Padrão (Para teste)
        cliente, _ = Cliente.objects.get_or_create(
            cpf="00000000000",
            defaults={'nome': "Cliente WhatsApp", 'telefone': "000000000"}
        )

        # 3. Cria o Pedido no Banco de Dados
        pedido = Pedido.objects.create(
            cliente=cliente,
            prazo_entrega=timezone.now().date() + timezone.timedelta(days=15), # Chute de 15 dias
            status='ORCAMENTO',
            horas_estimadas=Decimal(dados_ia['horas_estimadas']),
            observacoes=f"Gerado por IA.\nResumo: {dados_ia['resumo_peca']}\nMateriais Sugeridos: {', '.join(dados_ia['materiais_sugeridos'])}"
        )

        # 4. Garante um Template Padrão
        template, _ = TemplateMedida.objects.get_or_create(nome="Padrão IA")

        # 5. Cria a Ficha Técnica com a Imagem
        ficha = FichaTecnica.objects.create(
            pedido=pedido,
            template=template,
            descricao_visual=dados_ia['descricao_visual'],
            croqui_imagem=imagem_croqui # Aqui entra a imagem do DALL-E
        )

        # Força o recálculo do preço
        pedido.save()

        self.stdout.write(self.style.SUCCESS(f"✅ SUCESSO! Pedido #{pedido.id} criado."))
        self.stdout.write(f"💰 Valor Orçado: R$ {pedido.valor_total}")
        self.stdout.write(f"👗 Peça: {dados_ia['resumo_peca']}")
        self.stdout.write(f"🎨 Croqui salvo no sistema.")
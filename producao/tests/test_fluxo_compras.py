from django.test import TestCase
from decimal import Decimal
from core.models import Cliente
from producao.models import Material, Pedido, FichaTecnica, ItemFichaTecnica, MovimentacaoEstoque, TemplateMedida
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
from producao.services import PedidoService


class FluxoComprasTests(TestCase):
    def setUp(self):
        # 1. Cria Material com Estoque ZERO (Para testar o bloqueio)
        self.ziper = Material.objects.create(nome="Zíper Invisível", preco_custo=Decimal('2.00'), estoque_atual=0)

        # 2. Cria Cliente e Pedido
        self.cliente = Cliente.objects.create(nome="Cliente Teste", cpf="123")
        self.pedido = Pedido.objects.create(
            cliente=self.cliente,
            prazo_entrega=timezone.now().date() + timedelta(days=10),
            status='ORCAMENTO',
            quantidade=1
        )

        # --- CORREÇÃO AQUI: CRIAR TEMPLATE OBRIGATÓRIO ---
        self.template = TemplateMedida.objects.create(nome="Padrão", estrutura_medidas={})

        # 3. Cria Ficha Técnica (AGORA COM TEMPLATE)
        self.ficha = FichaTecnica.objects.create(
            pedido=self.pedido,
            template=self.template,  # <--- FALTAVA ISSO
            descricao_visual="Vestido"
        )

        # Consome 5 Zíperes
        ItemFichaTecnica.objects.create(ficha=self.ficha, material=self.ziper, quantidade=5)

    def test_bloqueio_sem_estoque(self):
        """O sistema deve PROIBIR mudar para CONFEC se não tiver material"""
        self.pedido.status = 'CONFEC'

        # Deve falhar ao tentar salvar
        with self.assertRaises(ValidationError) as erro:
            self.pedido.save()

        self.assertIn("ESTOQUE INSUFICIENTE", str(erro.exception))
        self.assertIn("Zíper Invisível", str(erro.exception))

    def test_liberacao_apos_compra(self):
        """Após comprar (MovimentacaoEstoque), deve permitir produção e baixar saldo"""

        # 1. Ação de Compra (Entrada no Estoque)
        MovimentacaoEstoque.objects.create(material=self.ziper, tipo='E', quantidade=10, observacao="Compra")

        # Verifica se estoque subiu para 10
        self.ziper.refresh_from_db()
        self.assertEqual(self.ziper.estoque_atual, 10)

        # 2. Tenta Produzir agora (Consome 5)
        from producao.services import PedidoService
        PedidoService.iniciar_confeccao(self.pedido)

        # 3. Verifica se baixou o estoque (10 - 5 = 5)
        self.ziper.refresh_from_db()
        self.assertEqual(self.ziper.estoque_atual, 5)
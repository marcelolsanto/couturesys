from decimal import Decimal
from django.utils import timezone
from .base import FinanceiroTestCase
from financeiro.models import ContaPagar, ContaReceber
from producao.models import Pedido
from producao.services import PedidoService


class AutomacaoFinanceiraTests(FinanceiroTestCase):

    def test_gerar_conta_pagar_ao_comprar_estoque(self):
        """
        Ao lançar entrada de estoque com valor, deve criar Conta a Pagar automaticamente.
        """
        # AÇÃO: Comprar 10m de seda (R$ 500,00)
        self.realizar_compra_material(qtd=10)

        # VERIFICAÇÃO
        # 1. Deve existir 1 conta a pagar
        self.assertEqual(ContaPagar.objects.count(), 1)

        # 2. O valor deve bater com a compra (R$ 500,00)
        conta = ContaPagar.objects.first()
        self.assertEqual(conta.valor, Decimal('500.00'))

        # 3. O status deve ser PENDENTE (pois acabamos de lançar)
        self.assertEqual(conta.status, 'PENDENTE')
        self.assertIn("Seda Pura", conta.descricao)

    def test_gerar_conta_receber_sinal_pedido(self):
        """
        Ao aprovar pedido com sinal, deve lançar a entrada no caixa como PAGO.
        """
        # AÇÃO: Vender vestido de R$ 1000 com R$ 300 de sinal
        pedido = Pedido.objects.create(
            cliente=self.cliente,
            status='ORCAMENTO',  # <--- Importante começar aqui
            valor_total=Decimal('1000.00'),
            valor_sinal=Decimal('300.00'),
            quantidade=1,
            prazo_entrega=timezone.now().date()
        )

        # 2. AÇÃO EXPLÍCITA (A Mágica Nova)
        PedidoService.aprovar_pedido(pedido)

        # 3. Verificação (Igual ao que era antes)
        self.assertEqual(ContaReceber.objects.count(), 1)
        conta = ContaReceber.objects.first()
        self.assertEqual(conta.status, 'PAGO')

    def test_nao_gerar_financeiro_se_estoque_sem_valor(self):
        """
        Se for apenas um ajuste de estoque (sem valor de compra),
        NÃO deve gerar boleto para pagar.
        """
        from producao.models import MovimentacaoEstoque

        # Ajuste de inventário (sobrou 1 metro, achei no chão)
        MovimentacaoEstoque.objects.create(
            material=self.material,
            tipo='E',
            quantidade=1,
            valor_compra_total=None,  # Sem custo financeiro
            observacao="Ajuste"
        )

        # Não deve ter conta a pagar
        self.assertEqual(ContaPagar.objects.count(), 0)
from django.test import TestCase
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta
from producao.models import Material, MovimentacaoEstoque, Pedido, ParametrosSistema
from core.models import Cliente
from financeiro.models import ContaPagar, ContaReceber
from producao.services import PedidoService

class AutomacaoFinanceiraTests(TestCase):
    def setUp(self):
        self.params = ParametrosSistema.get_solo()  # Necessário para criar pedidos
        self.cliente = Cliente.objects.create(nome="Pagador", cpf="123")
        self.material = Material.objects.create(nome="Ouro", preco_custo=100, estoque_atual=0)

    def test_compra_estoque_gera_conta_pagar(self):
        """Ao lançar Entrada com Valor, cria Conta a Pagar"""
        MovimentacaoEstoque.objects.create(
            material=self.material,
            tipo='E',
            quantidade=10,
            valor_compra_total=Decimal('1000.00'),  # Comprei R$ 1.000
            observacao="Compra Fornecedor X"
        )

        # Verifica financeiro
        conta = ContaPagar.objects.first()
        self.assertIsNotNone(conta)
        self.assertEqual(conta.valor, Decimal('1000.00'))
        self.assertIn("Ouro", conta.descricao)

    def test_aprovacao_pedido_gera_sinal(self):
        """Ao aprovar pedido com sinal, cria Conta a Receber"""
        # Cria como Rascunho
        pedido = Pedido.objects.create(
            cliente=self.cliente,
            status='ORCAMENTO',  # Começa como orçamento
            prazo_entrega=timezone.now().date(),
            valor_total=Decimal('5000.00'),
            valor_sinal=Decimal('2000.00'),
            quantidade=1
        )

        from producao.services import PedidoService
        PedidoService.aprovar_pedido(pedido)

        # Agora a assertion funciona
        self.assertEqual(ContaReceber.objects.count(), 1)

        conta = ContaReceber.objects.first()
        self.assertIsNotNone(conta)
        self.assertEqual(conta.valor, Decimal('2000.00'))
        self.assertEqual(conta.descricao, "Sinal")
        self.assertEqual(conta.status, 'PAGO')  # Sinal entra como pago
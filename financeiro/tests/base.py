from django.test import TestCase
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta
from core.models import Cliente
from producao.models import Material, Pedido, MovimentacaoEstoque, ParametrosSistema  # <--- Adicione ParametrosSistema
from financeiro.models import CategoriaFinanceira, ContaPagar, ContaReceber


class FinanceiroTestCase(TestCase):
    def setUp(self):
        # 0. Configura o Sistema (Obrigatório para evitar erro de float vs Decimal)
        ParametrosSistema.objects.create(
            custo_hora_padrao=Decimal('35.00'),
            taxa_imposto_padrao=Decimal('0.10'),
            custo_fixo_mensal=Decimal('1000.00'),
            meta_clientes_mes=Decimal('100')
        )

        # 1. Categoria Financeira
        self.cat_compra = CategoriaFinanceira.objects.create(nome="Compra Matéria Prima", tipo='D')

        # 2. Dados Básicos de Produção
        self.cliente = Cliente.objects.create(nome="Cliente Pagador", cpf="11122233344")
        self.material = Material.objects.create(
            nome="Seda Pura",
            preco_custo=Decimal('50.00'),
            estoque_atual=Decimal('0')
        )

    def realizar_compra_material(self, qtd=10):
        """Simula uma entrada no estoque (Compra)"""
        valor_total = qtd * self.material.preco_custo

        MovimentacaoEstoque.objects.create(
            material=self.material,
            tipo='E',  # Entrada
            quantidade=Decimal(qtd),
            valor_compra_total=valor_total,
            observacao="Compra Teste"
        )

    def realizar_venda_pedido(self, sinal=0):
        """Simula um pedido aprovado"""
        prazo = timezone.now().date() + timedelta(days=20)
        return Pedido.objects.create(
            cliente=self.cliente,
            status='APROVADO',
            quantidade=1,
            valor_total=Decimal('1000.00'),
            valor_sinal=Decimal(sinal),
            prazo_entrega=prazo
        )
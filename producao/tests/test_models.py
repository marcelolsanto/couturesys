from decimal import Decimal
from django.core.exceptions import ValidationError
from .base import ProducaoTestCase


class PedidoUnitTests(ProducaoTestCase):

    def test_calculo_custo_operacional(self):
        """Testa se a matemática do custo total está exata"""
        pedido = self.criar_pedido_completo(qtd=10)  # 10 peças

        # Cálculos Esperados por Peça:
        # Material: 2m * R$ 20,00 = R$ 40,00
        # MO: 2h * R$ 35,00 = R$ 70,00
        # Frete: R$ 5,00
        # Rateio: 1000/100 = R$ 10,00
        # Total Unitário: 40 + 70 + 5 + 10 = R$ 125,00
        # Total Lote (10 peças): R$ 1.250,00

        custo_calculado = pedido.calcular_custo_operacional_total()
        self.assertEqual(custo_calculado, Decimal('1250.00'))

    def test_congelamento_custos_snapshot(self):
        """Testa se o pedido mantém o preço antigo mesmo se o custo global subir"""
        # Cria pedido com preço atual (35.00)
        pedido = self.criar_pedido_completo(status='APROVADO')
        self.assertEqual(pedido.CUSTO_HORA, Decimal('35.00'))

        # Agora a inflação subiu!
        # CORREÇÃO: Atualizar o self.params que já pegamos via get_solo() no base.py
        self.params.custo_hora_padrao = Decimal('100.00')
        self.params.save()

        # O pedido antigo NÃO pode mudar
        pedido.refresh_from_db()
        self.assertEqual(pedido.CUSTO_HORA, Decimal('35.00'))

        # Um novo pedido deve pegar o preço novo
        novo_pedido = self.criar_pedido_completo(status='ORCAMENTO')
        self.assertEqual(novo_pedido.CUSTO_HORA, Decimal('100.00'))
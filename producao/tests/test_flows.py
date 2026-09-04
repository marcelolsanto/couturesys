from decimal import Decimal
from .base import ProducaoTestCase
from producao.models import MovimentacaoEstoque
from producao.services import PedidoService


class FluxoEstoqueTests(ProducaoTestCase):

    def test_baixa_estoque_automatica(self):
        """Ao mudar para CONFEC, deve baixar estoque e criar histórico"""
        pedido = self.criar_pedido_completo(qtd=10, status='APROVADO')

        # Estoque Inicial: 100
        # Consumo Previsto: 10 peças * 2m = 20m

        # AÇÃO: Iniciar Produção
        PedidoService.iniciar_confeccao(pedido)

        self.tecido.refresh_from_db()
        self.assertEqual(self.tecido.estoque_atual, Decimal('80.00'))

        self.tecido.refresh_from_db()

        # 1. Verifica se baixou o saldo
        self.assertEqual(self.tecido.estoque_atual, Decimal('80.00'))  # 100 - 20

        # 2. Verifica se criou o registro de auditoria
        movimentacao = MovimentacaoEstoque.objects.last()
        self.assertEqual(movimentacao.tipo, 'S')
        self.assertEqual(movimentacao.quantidade, Decimal('20.00'))
        self.assertIn("Produção Pedido", movimentacao.observacao)

    def test_estorno_cancelamento(self):
        """Ao CANCELAR um pedido em produção, deve devolver o material"""
        # Começa já em produção (estoque já baixado para 80)
        pedido = self.criar_pedido_completo(qtd=10, status='ORCAMENTO')
        from producao.services import PedidoService  # Importe no topo
        # Inicia confecção via serviço
        PedidoService.iniciar_confeccao(pedido)

        # AÇÃO: Cancelar via serviço (NÃO MAIS via .save())
        PedidoService.cancelar_pedido(pedido)

        self.tecido.refresh_from_db()
        # ... verificações ...

        # Verifica se voltou para 100
        self.assertEqual(self.tecido.estoque_atual, Decimal('100.00'))

        # Verifica registro de Entrada
        mov = MovimentacaoEstoque.objects.first()  # O último criado (devido à ordenação padrão ou logicamente o mais recente)
        # Nota: Ideal filtrar pelo ID ou timestamps se houver muitos

        self.assertEqual(MovimentacaoEstoque.objects.count(), 2)  # 1 Saída + 1 Entrada
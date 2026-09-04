from django.test import TestCase
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
from core.models import Cliente
from producao.models import Material, Pedido, ParametrosSistema, TemplateMedida, FichaTecnica, ItemFichaTecnica, \
    MovimentacaoEstoque
from producao.services import PedidoService


class ProducaoTests(TestCase):
    def setUp(self):
        # 1. Configurações Globais (CORRIGIDO)
        # Em vez de criar uma nova (create), pegamos a existente (get_solo) e atualizamos
        self.params = ParametrosSistema.get_solo()
        self.params.custo_hora_padrao = Decimal('35.00')
        self.params.taxa_imposto_padrao = Decimal('0.10')
        self.params.custo_fixo_mensal = Decimal('1000.00') # Para dar R$ 10 de rateio
        self.params.meta_clientes_mes = Decimal('100')
        self.params.save()

        # 2. Dados Base
        self.tecido = Material.objects.create(nome="Seda", preco_custo=Decimal('50.00'), estoque_atual=0)
        self.cliente = Cliente.objects.create(nome="Cliente Vip", cpf="000")
        self.template = TemplateMedida.objects.create(nome="Padrão")

        # 3. Pedido Rascunho
        self.pedido = Pedido.objects.create(
            cliente=self.cliente,
            prazo_entrega=timezone.now().date() + timedelta(days=15),
            status='ORCAMENTO',
            quantidade=1,
            horas_estimadas=Decimal('10.00'),  # 10h * 35 = 350 MO
            custo_transporte=Decimal('50.00')
        )

        # 4. Ficha Técnica (Consome 2m de Seda = R$ 100,00)
        self.ficha = FichaTecnica.objects.create(pedido=self.pedido, template=self.template, descricao_visual="Teste")
        ItemFichaTecnica.objects.create(ficha=self.ficha, material=self.tecido, quantidade=2)

    def test_calculo_custo_exato(self):
        """
        Verifica a matemática financeira do pedido:
        Material (100) + MO (350) + Frete (50) + Rateio (10) = 510,00
        """
        custo = self.pedido.calcular_custo_operacional_total()
        # Rateio = 1000 / 100 = 10.00
        self.assertEqual(custo, Decimal('510.00'))

    def test_bloqueio_producao_sem_estoque(self):
        """Não pode mudar para CONFEC se estoque é 0"""
        self.pedido.status = 'CONFEC'
        with self.assertRaises(ValidationError):
            self.pedido.save()

    def test_fluxo_compra_e_baixa_automatica(self):
        """
        Cenário Real:
        1. Identifica falta -> 2. Compra -> 3. Produz -> 4. Verifica Baixa
        """
        # 1. Compra o material (Entrada)
        MovimentacaoEstoque.objects.create(
            material=self.tecido, tipo='E', quantidade=10, observacao="Compra"
        )
        self.tecido.refresh_from_db()
        self.assertEqual(self.tecido.estoque_atual, 10)

        # 2. Inicia Produção (Consome 2)
        from producao.services import PedidoService
        PedidoService.iniciar_confeccao(self.pedido)  # Agora deve passar!

        # 3. Verifica Baixa
        self.tecido.refresh_from_db()
        self.assertEqual(self.tecido.estoque_atual, 8)  # 10 - 2

        # Verifica Histórico
        self.assertTrue(MovimentacaoEstoque.objects.filter(tipo='S', observacao__contains="Produção").exists())
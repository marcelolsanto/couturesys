from django.test import TestCase
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta
from core.models import Cliente
from producao.models import Material, Pedido, ParametrosSistema, TemplateMedida, FichaTecnica, ItemFichaTecnica


class ProducaoTestCase(TestCase):
    def setUp(self):
        # 1. Configurações do Sistema (CORRIGIDO)
        self.params = ParametrosSistema.get_solo()
        self.params.custo_hora_padrao = Decimal('35.00')
        self.params.taxa_imposto_padrao = Decimal('0.10')
        self.params.custo_fixo_mensal = Decimal('1000.00')
        self.params.meta_clientes_mes = Decimal('100') # Importante para o rateio dar R$ 10,00
        self.params.save()

        # 2. Cliente e Material
        self.cliente = Cliente.objects.create(nome="Cliente Teste", cpf="12345678900")
        self.tecido = Material.objects.create(
            nome="Tecido Teste",
            preco_custo=Decimal('20.00'),
            unidade='M',
            estoque_atual=Decimal('100.00')
        )

        # 3. Template
        self.template = TemplateMedida.objects.create(nome="Padrão", estrutura_medidas={})

    def criar_pedido_completo(self, qtd=10, status='ORCAMENTO'):
        prazo = timezone.now().date() + timedelta(days=10)

        pedido = Pedido.objects.create(
            cliente=self.cliente,
            quantidade=qtd,
            horas_estimadas=Decimal('2.00'),
            custo_transporte=Decimal('5.00'),
            status=status,
            valor_total=Decimal('5000.00'),
            prazo_entrega=prazo
        )

        ficha = FichaTecnica.objects.create(pedido=pedido, template=self.template, descricao_visual="Teste")

        ItemFichaTecnica.objects.create(
            ficha=ficha,
            material=self.tecido,
            quantidade=Decimal('2.00')
        )

        # --- CORREÇÃO IMPORTANTE ---
        # Recarrega o pedido do banco para ele "perceber" que agora tem uma ficha técnica
        pedido.refresh_from_db()

        return pedido
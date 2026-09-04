from django.test import Client
from django.urls import reverse
from decimal import Decimal
from django.utils import timezone
from django.contrib.auth.models import User  # <--- Importante
from .base import FinanceiroTestCase
from financeiro.models import ContaPagar, ContaReceber


class DashboardTests(FinanceiroTestCase):
    def setUp(self):
        super().setUp()
        self.client = Client()
        self.hoje = timezone.now().date()

        # --- ATUALIZAÇÃO DE SEGURANÇA ---
        # Criamos um admin e logamos, pois o dashboard agora é protegido
        self.admin_user = User.objects.create_superuser('admin_dash', 'admin@test.com', 'senha123')
        self.client.force_login(self.admin_user)

    def test_calculo_saldo_real(self):
        """
        O Dashboard deve mostrar: (Recebido - Pago) = Saldo Real
        """
        # CENÁRIO:
        # 1. Recebi R$ 1.000,00 (Venda à vista)
        # Precisamos de um pedido dummy para a ContaReceber (integridade do banco)
        from producao.models import Pedido
        pedido_dummy = Pedido.objects.create(
            cliente=self.cliente, status='ENTREGUE',
            quantidade=1, valor_total=Decimal('1000.00'), prazo_entrega=self.hoje
        )

        ContaReceber.objects.create(
            pedido=pedido_dummy,
            descricao="Venda", valor=Decimal('1000.00'),
            data_vencimento=self.hoje, status='PAGO'
        )

        # 2. Paguei R$ 200,00 (Luz)
        ContaPagar.objects.create(
            descricao="Luz", categoria=self.cat_compra,
            valor=Decimal('200.00'), data_vencimento=self.hoje,
            status='PAGO'
        )

        # 3. Tenho uma conta PENDENTE de R$ 5.000 (Não deve afetar o saldo real ainda)
        ContaPagar.objects.create(
            descricao="Máquina Nova", categoria=self.cat_compra,
            valor=Decimal('5000.00'), data_vencimento=self.hoje,
            status='PENDENTE'
        )

        # AÇÃO: Carregar Dashboard
        response = self.client.get(reverse('financeiro_dashboard'))

        self.assertEqual(response.status_code, 200)

        # Como o Django Admin renderiza o HTML, precisamos decodificar
        html = response.content.decode('utf-8')

        # VERIFICAÇÃO (R$ 1000 - R$ 200 = R$ 800)
        # Verifica se R$ 800,00 está na tela (Saldo)
        self.assertIn("800,00", html)

        # Verifica se R$ 5.000,00 está na tela (Previsão de Saída)
        self.assertIn("5.000,00", html)
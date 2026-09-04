from django.test import TestCase
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.models import User
from core.models import Cliente
from producao.models import Pedido, ParametrosSistema
from juridico.models import Contrato, ModeloContrato


class JuridicoTestCase(TestCase):
    def setUp(self):
        # 0. Configurações Globais (Evita erros de Decimal)
        ParametrosSistema.objects.create(
            custo_hora_padrao=Decimal('35.00'),
            taxa_imposto_padrao=Decimal('0.10'),
            custo_fixo_mensal=Decimal('1000.00'),
            meta_clientes_mes=Decimal('100')
        )

        # 1. Usuário Admin (Para assinar/criar)
        self.advogado = User.objects.create_superuser('advogado', 'lei@teste.com', 'senha123')

        # 2. Cliente
        self.cliente = Cliente.objects.create(
            nome="Empresa de Eventos LTDA",
            cpf="12345678901",
            endereco="Av. Paulista, 1000"
        )

        # 3. Pedido (Base do contrato)
        self.pedido = Pedido.objects.create(
            cliente=self.cliente,
            status='ORCAMENTO',
            quantidade=10,
            valor_total=Decimal('5000.00'),
            prazo_entrega=timezone.now().date() + timedelta(days=30)
        )

        # 4. Modelo de Contrato (Template)
        self.modelo_padrao = ModeloContrato.objects.create(
            nome="Prestação de Serviços Padrão",
            conteudo="Contrato entre a CoutureSys e {nome_cliente}. Valor total: {valor_total}."
        )

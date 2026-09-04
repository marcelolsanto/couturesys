from django.test import TestCase
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta
from core.models import Cliente
from producao.models import Pedido, ParametrosSistema
from financeiro.models import ContaReceber, ContaPagar
from juridico.models import Contrato, ModeloContrato


class AutomacaoJuridicoTests(TestCase):
    def setUp(self):
        # CORREÇÃO: Usar get_solo() e atualizar, em vez de criar um novo
        config = ParametrosSistema.get_solo()
        config.custo_hora_padrao = Decimal('10.00') # Teste quer 10, não 35
        config.taxa_imposto_padrao = Decimal('0.10')
        config.custo_fixo_mensal = Decimal('1000.00')
        config.meta_clientes_mes = Decimal('100')
        config.save() # Salva no ID 1

        self.cliente = Cliente.objects.create(nome="Noiva Teste", cpf="99988877700")

        # Pedido de R$ 1.000,00 com R$ 300,00 de sinal
        # Custos: 10 horas MO (R$ 100) + R$ 50 Frete
        self.pedido = Pedido.objects.create(
            cliente=self.cliente,
            status='ORCAMENTO',
            quantidade=1,
            valor_total=Decimal('1000.00'),
            valor_sinal=Decimal('300.00'),  # TEM SINAL
            horas_estimadas=Decimal('10'),  # Custo MO = 10 * 10 = 100
            custo_transporte=Decimal('50.00'),  # Custo Frete = 50
            prazo_entrega=timezone.now().date() + timedelta(days=30)
        )
        self.modelo = ModeloContrato.objects.create(nome="Padrão", conteudo="Teste")

    def test_gerar_financeiro_complexo_ao_assinar(self):
        """
        Ao assinar, deve gerar:
        RECEBER:
          1. Sinal (300,00)
          2. Restante (700,00)
        PAGAR:
          1. Imposto (100,00 - 10%)
          2. Mão de Obra (100,00)
          3. Frete (50,00)
        """
        # 1. Cria e Assina
        contrato = Contrato.objects.create(pedido=self.pedido, modelo=self.modelo, status='ASSINADO')

        # 2. VERIFICAÇÃO DE ENTRADAS (RECEITAS)
        self.assertEqual(ContaReceber.objects.count(), 2)  # Sinal + Restante

        sinal = ContaReceber.objects.get(descricao__startswith="Sinal")
        self.assertEqual(sinal.valor, Decimal('300.00'))

        restante = ContaReceber.objects.get(descricao__startswith="Restante")
        self.assertEqual(restante.valor, Decimal('700.00'))
        self.assertEqual(restante.data_vencimento, self.pedido.prazo_entrega)

        # 3. VERIFICAÇÃO DE SAÍDAS (CUSTOS)
        # Esperamos: Imposto, Frete, Mão de Obra (Materiais não, pois não criei ficha técnica no teste)
        self.assertEqual(ContaPagar.objects.count(), 3)

        # Verifica valores individuais
        imposto = ContaPagar.objects.get(descricao__startswith="Impostos")
        self.assertEqual(imposto.valor, Decimal('100.00'))  # 10% de 1000

        frete = ContaPagar.objects.get(descricao__startswith="Frete")
        self.assertEqual(frete.valor, Decimal('50.00'))

        mo = ContaPagar.objects.get(descricao__startswith="Mão de Obra")
        self.assertEqual(mo.valor, Decimal('100.00'))  # 10h * R$ 10
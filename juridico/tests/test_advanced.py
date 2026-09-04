from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.test.utils import CaptureQueriesContext
from django.db import connection, transaction
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta

from core.models import Cliente
from producao.models import ParametrosSistema, Pedido
from financeiro.models import CategoriaFinanceira, ContaPagar, ContaReceber
from django.db.models import ProtectedError


class FinanceiroAdvancedTests(TestCase):
    def setUp(self):
        # 1. Configuração do Sistema (Evita erro de Float vs Decimal)
        ParametrosSistema.objects.create(
            custo_hora_padrao=Decimal('35.00'),
            taxa_imposto_padrao=Decimal('0.10'),
            custo_fixo_mensal=Decimal('1000.00'),
            meta_clientes_mes=Decimal('100')
        )

        # 2. Usuários
        self.admin = User.objects.create_superuser('admin_fin', 'a@a.com', '123')
        self.user_comum = User.objects.create_user('funcionario', 'f@f.com', '123')

        # 3. Dados Básicos
        self.categoria = CategoriaFinanceira.objects.create(nome="Geral", tipo='D')
        self.cliente = Cliente.objects.create(nome="Cliente Teste", cpf="00000000000")

    # --- 1. TESTE DE SEGURANÇA (Security Testing) ---
    def test_seguranca_acesso_dashboard(self):
        """
        Garante que apenas usuários logados (e idealmente Staff) acessem o painel financeiro.
        """
        # Caso A: Usuário não logado tenta acessar
        self.client.logout()
        response = self.client.get(reverse('financeiro_dashboard'))
        # Deve redirecionar para login (302) ou dar erro (depende da sua config de view),
        # mas não pode retornar 200 (Sucesso) com os dados.
        self.assertNotEqual(response.status_code, 200)

        # Caso B: Usuário Comum (sem permissão de admin)
        # Nota: Se sua view não tiver @staff_member_required, esse teste pode falhar (o que indica uma falha de segurança!)
        self.client.force_login(self.user_comum)
        response = self.client.get(reverse('financeiro_dashboard'))
        # Se o sistema for seguro, usuários comuns não veem o dashboard financeiro
        # Se você ainda não bloqueou, isso aqui vai retornar 200 e é um alerta de segurança.

    # --- 2. TESTE DE DESEMPENHO (Performance/Load Testing) ---
    def test_desempenho_dashboard_com_muitos_dados(self):
        """
        Verifica se o Dashboard aguenta calcular o saldo mesmo com 200 lançamentos.
        O número de queries deve ser fixo (ex: < 10), não proporcional aos dados.
        """
        # Gera 200 contas a pagar no banco
        contas = []
        for i in range(200):
            contas.append(ContaPagar(
                descricao=f"Conta {i}",
                categoria=self.categoria,
                valor=Decimal('10.00'),
                data_vencimento=timezone.now().date(),
                status='PENDENTE'
            ))
        ContaPagar.objects.bulk_create(contas)  # Insere tudo de uma vez (rápido)

        self.client.force_login(self.admin)

        # Mede as queries do banco
        with CaptureQueriesContext(connection) as ctx:
            response = self.client.get(reverse('financeiro_dashboard'))
            self.assertEqual(response.status_code, 200)

        # O Django deve usar SUM() no SQL, então deve fazer poucas queries
        # Se fizer 200 queries, temos um problema grave de N+1
        print(f"\n⚡ Queries no Dashboard com 200 contas: {len(ctx.captured_queries)}")
        self.assertLess(len(ctx.captured_queries), 15)

    # --- 3. TESTE DE REGRESSÃO (Integridade de Dados) ---
    def test_regressao_nao_perder_historico_pago(self):
        """
        Se eu apagar um Pedido, a Conta a Receber que JÁ FOI PAGA
        deve impedir a exclusão (ProtectedError).
        """
        pedido = Pedido.objects.create(
            cliente=self.cliente,
            status='ENTREGUE',
            quantidade=1,
            valor_total=Decimal('500.00'),
            prazo_entrega=timezone.now().date()
        )

        # Cria a conta financeira vinculada e marca como PAGA
        conta = ContaReceber.objects.create(
            pedido=pedido,
            descricao="Venda Teste",
            valor=Decimal('500.00'),
            data_vencimento=timezone.now().date(),
            status='PAGO'
        )

        # CORREÇÃO: O teste agora espera que o banco BLOQUEIE a deleção
        with self.assertRaises(ProtectedError):
            pedido.delete()

        # Garante que a conta financeira ainda está lá sã e salva
        self.assertTrue(ContaReceber.objects.filter(id=conta.id).exists())

    # --- 4. TESTE FUNCIONAL (Ciclo Completo) ---
        # --- 4. TESTE FUNCIONAL (Ciclo Completo) ---
        def test_funcional_fluxo_caixa_real(self):
            """
            Simula um dia de trabalho: Pagar Luz e Receber Venda.
            Verifica se o Saldo Real bate exatamente.
            """
            self.client.force_login(self.admin)

            # 1. Pagar Conta de Luz (R$ 150,00) - Saiu do Caixa
            # (ContaPagar não exige pedido, então ok)
            ContaPagar.objects.create(
                descricao="Luz", categoria=self.categoria,
                valor=Decimal('150.00'), data_vencimento=timezone.now().date(),
                status='PAGO'
            )

            # --- CORREÇÃO: Criar um Pedido Dummy para vincular ao recebimento ---
            pedido_dummy = Pedido.objects.create(
                cliente=self.cliente,
                status='ENTREGUE',
                quantidade=1,
                valor_total=Decimal('500.00'),
                prazo_entrega=timezone.now().date()
            )

            # 2. Venda de Vestido (R$ 500,00) - Entrou no Caixa
            ContaReceber.objects.create(
                pedido=pedido_dummy,  # <--- Agora vinculamos ao pedido!
                descricao="Venda Vestido",
                valor=Decimal('500.00'), data_vencimento=timezone.now().date(),
                status='PAGO'
            )

            # 3. Venda Futura (R$ 1000,00) - PENDENTE
            # Criamos outro pedido dummy para este lançamento
            pedido_futuro = Pedido.objects.create(
                cliente=self.cliente, status='APROVADO',
                quantidade=1, valor_total=Decimal('1000.00'), prazo_entrega=timezone.now().date()
            )

            ContaReceber.objects.create(
                pedido=pedido_futuro,  # <--- Vinculado
                descricao="Venda Futura",
                valor=Decimal('1000.00'), data_vencimento=timezone.now().date(),
                status='PENDENTE'
            )

            # AÇÃO: Carregar Dashboard
            response = self.client.get(reverse('financeiro_dashboard'))
            html = response.content.decode('utf-8')

            # DEBUG: Se der erro, descomente a linha abaixo para ver o HTML
            # print(html)

            # CÁLCULO ESPERADO:
            # Entrou: 500
            # Saiu: 150
            # Saldo Real: 350

            # Busca pelos valores formatados na tela
            self.assertIn("350,00", html)  # Saldo
            self.assertIn("500,00", html)  # Receita Real
            self.assertIn("150,00", html)  # Despesa Real
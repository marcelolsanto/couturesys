from django.contrib.auth.models import User
from django.test import Client
from django.test.utils import CaptureQueriesContext  # <--- Importante para contar queries
from django.db import connection
from decimal import Decimal
from django.urls import reverse
from django.core.exceptions import ValidationError
from .base import ProducaoTestCase
from producao.models import Pedido, MovimentacaoEstoque
from producao.services import PedidoService


class AdvancedTests(ProducaoTestCase):

    # --- 1. TESTE DE SEGURANÇA ---
    def test_seguranca_acesso_nao_autorizado(self):
        """
        Garante que um usuário sem permissão NÃO consiga deletar um pedido.
        """
        user_invasor = User.objects.create_user('estagiario', 'e@teste.com', 'senha123')
        self.client.login(username='estagiario', password='senha123')

        pedido = self.criar_pedido_completo()

        url_delete = reverse('admin:producao_pedido_delete', args=[pedido.id])
        self.client.post(url_delete, {'post': 'yes'})

        # O pedido ainda deve existir
        self.assertTrue(Pedido.objects.filter(id=pedido.id).exists())

    # --- 2. TESTE DE REGRESSÃO (CORRIGIDO) ---
    def test_regressao_edicao_sem_duplicar_estoque(self):
        """
        Garante que editar um pedido já em produção NÃO baixe o estoque novamente.
        """
        # 1. Cria em ORCAMENTO (Estoque intacto: 100)
        pedido = self.criar_pedido_completo(qtd=10, status='ORCAMENTO')

        # 2. Transita para CONFEC
        # CORREÇÃO: Apague 'pedido.status = ...' e use o Serviço
        PedidoService.iniciar_confeccao(pedido)
        # (Nota: aqui não precisa de 'self.' porque 'pedido' é uma variável local criada na linha acima)

        self.tecido.refresh_from_db()
        estoque_antes = self.tecido.estoque_atual
        self.assertEqual(estoque_antes, Decimal('80.00'), "Estoque inicial não baixou corretamente")

        # 3. AÇÃO DE REGRESSÃO: Editar apenas uma observação
        pedido.observacoes = "Alteração simples não deve afetar estoque"
        pedido.save()

        # 4. Verificação: O estoque deve permanecer IDÊNTICO
        self.tecido.refresh_from_db()
        self.assertEqual(self.tecido.estoque_atual, estoque_antes, "Estoque foi alterado indevidamente na edição")

        # Verifica se NÃO criou uma nova linha de movimentação duplicada
        # Deve haver apenas 1 movimentação de 'Saída'
        self.assertEqual(MovimentacaoEstoque.objects.filter(tipo='S').count(), 1)

    # --- 3. TESTE DE DESEMPENHO (CORRIGIDO) ---
    def test_desempenho_queries_n_plus_1(self):
        """
        Verifica se listar pedidos não mata o banco de dados.
        """
        # Cria 20 pedidos
        for i in range(20):
            self.criar_pedido_completo(qtd=1, status='ORCAMENTO')

        admin_user = User.objects.create_superuser('admin_teste', 'a@a.com', 'senha123')
        self.client.login(username='admin_teste', password='senha123')

        # Usa CaptureQueriesContext para contar manualmente
        with CaptureQueriesContext(connection) as ctx:
            response = self.client.get(reverse('admin:producao_pedido_changelist'))
            self.assertEqual(response.status_code, 200)

        # Análise:
        # Se for N+1, teremos 20 pedidos * X queries = +20 queries
        # Se estiver otimizado, teremos um número fixo baixo (ex: < 15)
        print(f"\nQueries executadas: {len(ctx.captured_queries)}")
        self.assertLess(len(ctx.captured_queries), 20, "Alerta de Performance: Muitas queries executadas na listagem!")

    # --- 4. SMOKE TESTING ---
    def test_smoke_paginas_principais(self):
        """Verifica se as páginas principais abrem sem erro 500"""
        admin_user = User.objects.create_superuser('smoke_user', 's@s.com', 'senha123')
        self.client.login(username='smoke_user', password='senha123')

        urls = [
            reverse('admin:index'),
            reverse('admin:producao_pedido_changelist'),
            reverse('admin:producao_material_changelist'),
        ]

        for url in urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, f"A URL {url} quebrou!")

    # --- 5. TESTE FUNCIONAL ---
    def test_funcional_ciclo_vida_pedido(self):
        """Simula a vida completa: Venda -> Produção -> Entrega -> Bloqueio"""
        # 1. Venda
        pedido = self.criar_pedido_completo(qtd=5, status='ORCAMENTO')
        self.assertEqual(pedido.status, 'ORCAMENTO')

        # 2. Produção (Baixa Estoque 100 - 10 = 90)
        from producao.services import PedidoService  # Importe no topo
        PedidoService.iniciar_confeccao(pedido)
        self.tecido.refresh_from_db()
        self.assertEqual(self.tecido.estoque_atual, Decimal('90.00'))

        # 3. Entrega (Trava de Segurança)
        pedido.status = 'ENTREGUE'
        pedido.save()

        # 4. Tentativa de Fraude (Mudar valor após entrega)
        pedido.valor_total = Decimal('999999.00')
        with self.assertRaises(ValidationError):
            pedido.save()  # Deve ser bloqueado pelo models.clean()
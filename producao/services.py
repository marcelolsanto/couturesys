# producao/services.py
from django.db import transaction
from django.utils import timezone
from decimal import Decimal
from .models import Pedido, ParametrosSistema, MovimentacaoEstoque
from financeiro.models import ContaReceber, CategoriaFinanceira


class PedidoService:
    @staticmethod
    def aprovar_pedido(pedido, user=None):
        """
        Orquestra a aprovação: Congela preços e gera financeiro.
        """
        with transaction.atomic():
            # 1. Congelamento de Custos (Snapshot)
            config = ParametrosSistema.get_solo()
            pedido.custo_hora_frozen = config.custo_hora_calculado
            pedido.taxa_imposto_frozen = config.taxa_imposto_padrao
            pedido.custo_fixo_frozen = config.custo_fixo_total
            pedido.meta_clientes_frozen = Decimal('80')

            # 2. Atualiza Status
            pedido.status = 'APROVADO'
            pedido.save()

            # 3. Gera Financeiro (Sinal)
            if pedido.valor_sinal > 0:
                # A verificação de duplicidade é feita aqui no banco:
                if not ContaReceber.objects.filter(pedido=pedido, descricao="Sinal").exists():
                    cat_venda, _ = CategoriaFinanceira.objects.get_or_create(
                        nome="Receita de Vendas", defaults={'tipo': 'R'}
                    )
                    ContaReceber.objects.create(
                        pedido=pedido,
                        categoria=cat_venda,
                        descricao="Sinal",
                        valor=pedido.valor_sinal,
                        data_vencimento=pedido.data_pedido.date(),
                        data_recebimento=pedido.data_pedido.date(),
                        status='PAGO'
                    )
        return pedido

    @staticmethod
    def gerar_parcelas_receber(pedido):
        valor_parcela = pedido.valor_total / pedido.qtd_parcelas
        categoria, _ = CategoriaFinanceira.objects.get_or_create(nome="Receita de Vendas")

        for i in range(pedido.qtd_parcelas):
            data_vencimento = pedido.data_pedido + timezone.timedelta(days=pedido.dias_intervalo * i)
            ContaReceber.objects.create(
                pedido=pedido,
                descricao=f"Parcela {i + 1}/{pedido.qtd_parcelas} - Pedido #{pedido.id}",
                valor=valor_parcela,
                data_vencimento=data_vencimento,
                status='PENDENTE',
                categoria=categoria
            )

    @staticmethod
    def iniciar_confeccao(pedido, user=None):
        """
        Transição de Aprovado -> Em Confecção com baixa de Estoque
        """
        # Validação de Estoque
        faltantes = pedido.gerar_roteiro_compras()
        if faltantes:
            raise ValueError(f"Estoque insuficiente para iniciar confecção do Pedido #{pedido.id}")

        with transaction.atomic():
            pedido.status = 'CONFEC'
            pedido.save()

            # Baixa no Estoque
            if hasattr(pedido, 'ficha_tecnica'):
                for item in pedido.ficha_tecnica.materiais_usados.all():
                    qtd_total = item.quantidade * pedido.quantidade
                    MovimentacaoEstoque.objects.create(
                        material=item.material,
                        tipo='S',  # Saída
                        quantidade=qtd_total,
                        usuario=user,
                        observacao=f"Produção Pedido #{pedido.id} (Via Service)"
                    )
        return pedido

    @staticmethod
    def cancelar_pedido(pedido, user=None):
        """
        Cancela o pedido e estorna materiais se já estiver em produção.
        """
        if pedido.status == 'CANCELADO':
            return pedido

        status_anterior = pedido.status

        with transaction.atomic():
            pedido.status = 'CANCELADO'
            pedido.save()

            # Se estava em produção, devolve os materiais (Estorno)
            if status_anterior == 'CONFEC' and hasattr(pedido, 'ficha_tecnica'):
                for item in pedido.ficha_tecnica.materiais_usados.all():
                    qtd_total = item.quantidade * pedido.quantidade
                    MovimentacaoEstoque.objects.create(
                        material=item.material,
                        tipo='E',  # Entrada (Devolução)
                        quantidade=qtd_total,
                        usuario=user,
                        observacao=f"Estorno Cancelamento Pedido #{pedido.id}"
                    )

            # Aqui você também poderia cancelar as contas financeiras em aberto

        return pedido
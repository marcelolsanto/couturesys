from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from decimal import Decimal
from .models import Contrato
from financeiro.models import ContaReceber, ContaPagar, CategoriaFinanceira


@receiver(post_save, sender=Contrato)
def gerar_financeiro_ao_assinar(sender, instance, created, **kwargs):
    """
    Automação Financeira Avançada:
    1. Divide a Receita em Sinal (À Vista) + Restante (Na Entrega).
    2. Explode os Custos em: Impostos, Materiais, Mão de Obra e Frete.
    """
    if instance.status == 'ASSINADO':
        pedido = instance.pedido

        # Evita duplicidade: Se já tem contas geradas para este pedido, não faz de novo.
        if ContaReceber.objects.filter(pedido=pedido).exists():
            return

        print(f"🔄 Iniciando automação financeira para o Contrato #{instance.id}...")

        # ==========================================
        # 1. CONTAS A RECEBER (ENTRADAS)
        # ==========================================

        # Categoria Padrão
        cat_venda, _ = CategoriaFinanceira.objects.get_or_create(
            nome="Receita de Vendas", defaults={'tipo': 'R'}
        )

        # A) Lançamento do SINAL (Se houver)
        if pedido.valor_sinal > 0:
            ContaReceber.objects.create(
                pedido=pedido,
                categoria=cat_venda,
                descricao=f"Sinal - Contrato #{instance.id} ({pedido.cliente.nome})",
                valor=pedido.valor_sinal,
                data_vencimento=timezone.now().date(),  # Vence Hoje
                status='PENDENTE'  # Pendente até confirmar no banco
            )

        # B) Lançamento do RESTANTE
        valor_restante = pedido.valor_total - pedido.valor_sinal
        if valor_restante > 0:
            ContaReceber.objects.create(
                pedido=pedido,
                categoria=cat_venda,
                descricao=f"Restante - Contrato #{instance.id} ({pedido.cliente.nome})",
                valor=valor_restante,
                data_vencimento=pedido.prazo_entrega,  # Vence na Entrega
                status='PENDENTE'
            )

        # ==========================================
        # 2. CONTAS A PAGAR (SAÍDAS / CUSTOS)
        # ==========================================
        data_previsao_pagto = timezone.now().date() + timezone.timedelta(days=15)  # Ex: Pagar custos em 15 dias

        # A) IMPOSTOS (Baseado na taxa configurada no pedido)
        valor_imposto = pedido.valor_total * pedido.TAXA_IMPOSTO
        if valor_imposto > 0:
            cat_imposto, _ = CategoriaFinanceira.objects.get_or_create(
                nome="Impostos e Taxas", defaults={'tipo': 'D'}
            )
            ContaPagar.objects.create(
                categoria=cat_imposto,
                descricao=f"Impostos s/ Pedido #{pedido.id}",
                valor=valor_imposto,
                data_vencimento=timezone.now().date() + timezone.timedelta(days=20),
                # Geralmente dia 20 do mês seguinte
                status='PENDENTE'
            )

        # B) FRETE / LOGÍSTICA
        if pedido.custo_transporte > 0:
            cat_frete, _ = CategoriaFinanceira.objects.get_or_create(
                nome="Fretes e Entregas", defaults={'tipo': 'D'}
            )
            ContaPagar.objects.create(
                categoria=cat_frete,
                descricao=f"Frete - Pedido #{pedido.id}",
                valor=pedido.custo_transporte * pedido.quantidade,
                data_vencimento=data_previsao_pagto,
                status='PENDENTE'
            )

        # C) MÃO DE OBRA (Costureiras)
        # Custo Hora * Horas Estimadas * Quantidade
        custo_mo_total = (pedido.CUSTO_HORA * pedido.horas_estimadas) * pedido.quantidade
        if custo_mo_total > 0:
            cat_servico, _ = CategoriaFinanceira.objects.get_or_create(
                nome="Serviços Tomados (Mão de Obra)", defaults={'tipo': 'D'}
            )
            ContaPagar.objects.create(
                categoria=cat_servico,
                descricao=f"Mão de Obra - Pedido #{pedido.id}",
                valor=custo_mo_total,
                data_vencimento=data_previsao_pagto,
                status='PENDENTE'
            )

        # D) MATERIAIS / FORNECEDORES (Via Ficha Técnica)
        # Verifica se o pedido tem ficha técnica vinculada e calcula o custo dos materiais
        custo_materiais_total = Decimal('0.00')
        if hasattr(pedido, 'ficha_tecnica') and pedido.ficha_tecnica:
            custo_unitario_mat = sum(item.custo_calculado for item in pedido.ficha_tecnica.materiais_usados.all())
            custo_materiais_total = custo_unitario_mat * pedido.quantidade

        if custo_materiais_total > 0:
            cat_fornecedor, _ = CategoriaFinanceira.objects.get_or_create(
                nome="Fornecedores (Matéria Prima)", defaults={'tipo': 'D'}
            )
            ContaPagar.objects.create(
                categoria=cat_fornecedor,
                descricao=f"Compra Materiais - Pedido #{pedido.id}",
                valor=custo_materiais_total,
                data_vencimento=timezone.now().date(),  # Compra Imediata
                status='PENDENTE'
            )

        print(f"✅ Automação Financeira Concluída para Contrato #{instance.id}")
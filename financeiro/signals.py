from django.db.models.signals import post_save
from django.dispatch import receiver
from datetime import timedelta
from producao.models import MovimentacaoEstoque, Pedido
from .models import ContaPagar, ContaReceber, CategoriaFinanceira


# 1. COMPROU MATERIAL -> GERA CONTA A PAGAR
@receiver(post_save, sender=MovimentacaoEstoque)
def gerar_conta_pagar_estoque(sender, instance, created, **kwargs):
    if created and instance.tipo == 'E' and instance.valor_compra_total:
        # Pega ou cria uma categoria padrão
        cat, _ = CategoriaFinanceira.objects.get_or_create(nome="Compra Materiais", tipo='D')

        ContaPagar.objects.create(
            descricao=f"Compra: {instance.material.nome}",
            categoria=cat,
            valor=instance.valor_compra_total,
            data_vencimento=instance.data.date() + timedelta(days=28),  # Sugere 28 dias
            origem_estoque=instance,
            status='PENDENTE'
        )
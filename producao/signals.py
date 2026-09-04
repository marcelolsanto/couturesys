from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.db import transaction
from .models import Pedido, MovimentacaoEstoque


@receiver(pre_save, sender=Pedido)
def rastrear_mudanca_status(sender, instance, **kwargs):
    """Guarda o status antigo antes de salvar para compararmos depois"""
    if instance.pk:
        try:
            old = Pedido.objects.get(pk=instance.pk)
            instance._status_anterior = old.status
        except Pedido.DoesNotExist:
            instance._status_anterior = None
    else:
        instance._status_anterior = None
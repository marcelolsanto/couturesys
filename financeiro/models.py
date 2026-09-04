from django.db import models
from django.utils import timezone
from decimal import Decimal

class CategoriaFinanceira(models.Model):
    TIPO_CHOICES = [('R', 'Receita'), ('D', 'Despesa')]
    nome = models.CharField(max_length=50)
    tipo = models.CharField(max_length=1, choices=TIPO_CHOICES)

    def __str__(self): return f"{self.get_tipo_display()} - {self.nome}"

class ContaPagar(models.Model):
    STATUS_CHOICES = [('PENDENTE', 'Pendente'), ('PAGO', 'Pago'), ('ATRASADO', 'Atrasado')]

    pedido = models.ForeignKey(
        'producao.Pedido',
        on_delete=models.PROTECT,
        related_name='contas_pagar',
        null=True, blank=True  # <--- CRÍTICO: Permite contas sem pedido (Luz, Aluguel)
    )
    descricao = models.CharField(max_length=100, verbose_name="Descrição")
    categoria = models.ForeignKey(CategoriaFinanceira, on_delete=models.PROTECT, limit_choices_to={'tipo': 'D'})
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    data_vencimento = models.DateField()
    data_pagamento = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDENTE')
    comprovante = models.FileField(upload_to='financeiro/pagar/', null=True, blank=True)

    # Vínculo opcional com compra de material (para rastreio)
    origem_estoque = models.ForeignKey('producao.MovimentacaoEstoque', on_delete=models.SET_NULL, null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.data_pagamento and self.status == 'PENDENTE':
            self.status = 'PAGO'
        super().save(*args, **kwargs)

    def __str__(self): return f"{self.descricao} (R$ {self.valor})"

    class Meta: verbose_name_plural = "Contas a Pagar"

class ContaReceber(models.Model):
    STATUS_CHOICES = [('PENDENTE', 'Pendente'), ('PAGO', 'Pago'), ('CANCELADO', 'Cancelado')]

    pedido = models.ForeignKey('producao.Pedido', on_delete=models.PROTECT, related_name='contas_receber')
    categoria = models.ForeignKey(CategoriaFinanceira, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Categoria")
    descricao = models.CharField(max_length=50)  # Ex: "Sinal", "Parcela 1/3"
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    data_vencimento = models.DateField()
    data_recebimento = models.DateField(null=True, blank=True)
    data_pagamento = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDENTE')

    def save(self, *args, **kwargs):
        if self.data_recebimento and self.status == 'PENDENTE':
            self.status = 'PAGO'
        super().save(*args, **kwargs)

    def __str__(self): return f"Ped #{self.pedido.id} - {self.descricao}"

    class Meta: verbose_name_plural = "Contas a Receber"
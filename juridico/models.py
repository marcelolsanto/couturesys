from django.db import models
from django.core.exceptions import ValidationError
from producao.models import Pedido

class ModeloContrato(models.Model):
    nome = models.CharField(max_length=100)
    conteudo = models.TextField(
        help_text="Use variáveis como {nome_cliente}, {cpf_cliente}, {valor_total} para substituição automática."
    )
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return self.nome

class Contrato(models.Model):
    STATUS_CHOICES = [
        ('RASCUNHO', 'Rascunho'),
        ('GERADO', 'Gerado (Aguardando Assinatura)'),
        ('ASSINADO', 'Assinado'),
        ('CANCELADO', 'Cancelado'),
    ]

    pedido = models.OneToOneField(Pedido, on_delete=models.CASCADE, related_name='contrato')
    modelo = models.ForeignKey(ModeloContrato, on_delete=models.PROTECT)
    conteudo_final = models.TextField(blank=True, null=True, verbose_name="Texto do Contrato")
    data_criacao = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='RASCUNHO')
    arquivo_pdf = models.FileField(upload_to='contratos/', blank=True, null=True)

    def __str__(self):
        return f"Contrato #{self.id} - {self.pedido.cliente.nome}"

    def clean(self):
        if self.pk:
            original = Contrato.objects.get(pk=self.pk)
            if original.status == 'ASSINADO' and self.conteudo_final != original.conteudo_final:
                raise ValidationError("Proibido alterar o texto de um contrato já ASSINADO.")

    def gerar_minuta(self):
        dados = {
            'nome_cliente': self.pedido.cliente.nome,
            'cpf_cliente': self.pedido.cliente.cpf,
            'endereco_cliente': self.pedido.cliente.endereco,
            'valor_total': f"R$ {self.pedido.valor_total:,.2f}",
            'data_entrega': self.pedido.prazo_entrega.strftime('%d/%m/%Y'),
        }
        try:
            self.conteudo_final = self.modelo.conteudo.format(**dados)
            self.status = 'GERADO'
            self.save()
        except KeyError as e:
            raise ValidationError(f"O modelo de contrato exige a variável {e}, mas ela não foi encontrada.")
from django.db import models


class Cliente(models.Model):
    nome = models.CharField(max_length=150)
    cpf = models.CharField(max_length=14, unique=True, help_text="Formato: 000.000.000-00")
    email = models.EmailField(blank=True, null=True)
    telefone = models.CharField(max_length=20, help_text="(DD) 99999-9999")
    endereco = models.TextField(blank=True, verbose_name="Endereço Completo")

    # Audit
    criado_em = models.DateTimeField(auto_now_add=True)
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.nome} ({self.cpf})"

    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"

from django.contrib import admin
from .models import Cliente


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    # Colunas que aparecem na lista
    list_display = ('nome', 'telefone', 'email', 'criado_em', 'ativo')

    # Barra de pesquisa (procura por nome ou CPF)
    search_fields = ('nome', 'cpf', 'email')

    # Filtros laterais
    list_filter = ('ativo', 'criado_em')

    # Link no nome para editar
    list_display_links = ('nome',)

    # Paginação (útil quando tiver centenas de clientes)
    list_per_page = 20
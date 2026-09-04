from django.contrib import admin
from django.utils.html import format_html
from django.urls import path
from django.shortcuts import redirect
from django.contrib import messages
from .models import CategoriaFinanceira, ContaPagar, ContaReceber
from producao.models import Pedido
from datetime import timedelta

@admin.register(CategoriaFinanceira)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'tipo')

@admin.register(ContaPagar)
class ContaPagarAdmin(admin.ModelAdmin):
    list_display = ('descricao', 'categoria', 'valor', 'data_vencimento', 'status_cor')
    list_filter = ('status', 'categoria', 'data_vencimento')

    def status_cor(self, obj):
        color = 'green' if obj.status == 'PAGO' else 'red'
        return format_html('<b style="color:{}">{}</b>', color, obj.get_status_display())

@admin.register(ContaReceber)
class ContaReceberAdmin(admin.ModelAdmin):
    list_display = ('descricao', 'pedido_link', 'valor', 'data_vencimento', 'status_cor')
    list_filter = ('status', 'data_vencimento')
    change_list_template = "admin/financeiro/contareceber_changelist.html"  # Vamos criar este template simples

    def pedido_link(self, obj):
        return f"{obj.pedido.cliente.nome} (Ped #{obj.pedido.id})"

    def status_cor(self, obj):
        color = 'green' if obj.status == 'PAGO' else 'orange'
        return format_html('<b style="color:{}">{}</b>', color, obj.get_status_display())

    # --- AÇÃO PERSONALIZADA: GERAR PARCELAS ---
    def get_urls(self):
        urls = super().get_urls()
        my_urls = [path('gerar-parcelas/<int:pedido_id>/', self.gerar_parcelas_view, name='gerar_parcelas'), ]
        return my_urls + urls

    def gerar_parcelas_view(self, request, pedido_id):
        pedido = Pedido.objects.get(pk=pedido_id)
        restante = pedido.valor_total - pedido.valor_sinal

        if restante <= 0:
            messages.warning(request, "Este pedido já está quitado (Sinal cobre tudo).")
            return redirect('admin:financeiro_contareceber_changelist')

        valor_parcela = restante / pedido.qtd_parcelas

        for i in range(pedido.qtd_parcelas):
            dias = (i + 1) * pedido.dias_intervalo
            vencimento = pedido.prazo_entrega  # Ou data_pedido + dias

            ContaReceber.objects.create(
                pedido=pedido,
                descricao=f"Parcela {i + 1}/{pedido.qtd_parcelas}",
                valor=valor_parcela,
                data_vencimento=vencimento,
                status='PENDENTE'
            )

        messages.success(request, f"{pedido.qtd_parcelas} parcelas geradas com sucesso para o Pedido #{pedido.id}")
        return redirect('admin:financeiro_contareceber_changelist')
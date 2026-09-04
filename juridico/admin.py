from django.contrib import admin
from django.utils.html import format_html
from core.utils import gerar_link_whatsapp  # <--- Importe aqui também
from .models import ModeloContrato, Contrato


# ... (Mantenha o ModeloContratoAdmin) ...

@admin.register(Contrato)
class ContratoAdmin(admin.ModelAdmin):
    # Adicionamos 'btn_zap_contrato' na lista
    list_display = ('__str__', 'status', 'botao_imprimir', 'btn_zap_contrato')
    readonly_fields = ('conteudo_final',)
    actions = ['gerar_minuta_action']

    def botao_imprimir(self, obj):
        # ... (Seu código anterior do botão imprimir) ...
        if obj.pk:
            return format_html('<a class="button" href="/juridico/imprimir/{}/" target="_blank">🖨️ Imprimir</a>',
                               obj.pk)
        return "-"

    botao_imprimir.short_description = "PDF"

    # 👇 ADICIONE ESTAS DUAS LINHAS NO FINAL DA CLASSE
    def has_add_permission(self, request):
        return False  # Isso remove o botão "Adicionar Contrato" da tela

    # --- NOVO BOTÃO WHATSAPP ---
    def btn_zap_contrato(self, obj):
        if not obj.pedido.cliente.telefone:
            return "-"

        msg = f"Olá {obj.pedido.cliente.nome}. Seu contrato #{obj.id} foi gerado e aguarda assinatura. Segue o link..."
        url = gerar_link_whatsapp(obj.pedido.cliente.telefone, msg)

        return format_html(
            '<a class="button" style="background-color: #25D366; color: white;" href="{}" target="_blank">'
            '📱 Avisar</a>',
            url
        )

    btn_zap_contrato.short_description = "WhatsApp"
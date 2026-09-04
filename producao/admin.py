from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.urls import reverse
from core.utils import gerar_link_whatsapp
from .models import (Pedido, FichaTecnica, RegistroProva, Material,
                     ItemFichaTecnica, TemplateMedida, ParametrosSistema,
                     MovimentacaoEstoque)
from .services import PedidoService


# --- CONFIGURAÇÃO DA FICHA TÉCNICA ---
class ItemFichaInline(admin.TabularInline):
    model = ItemFichaTecnica
    extra = 1
    autocomplete_fields = ['material']
    verbose_name = "Material Necessário"
    verbose_name_plural = "LISTA DE MATERIAIS (Consumo Unitário)"


@admin.register(FichaTecnica)
class FichaTecnicaAdmin(admin.ModelAdmin):
    inlines = [ItemFichaInline]
    list_display = ('pedido', 'template')
    search_fields = ('pedido__cliente__nome',)


# --- INLINES DO PEDIDO ---
class ProvaInline(admin.TabularInline):
    model = RegistroProva
    extra = 0
    verbose_name = "Agendamento"
    verbose_name_plural = "AGENDA DE PROVAS E ENTREGA"


class FichaInlineLink(admin.StackedInline):
    model = FichaTecnica
    extra = 0
    show_change_link = True
    verbose_name = "Definição Técnica (Clique em EDITAR para adicionar Tecidos)"
    fields = ['template', 'descricao_visual', 'tempo_estimado_horas', 'croqui_imagem', 'medidas_reais']


# --- PEDIDO PRINCIPAL ---
@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    inlines = [FichaInlineLink, ProvaInline]

    list_display = ('id', 'cliente', 'status_badge', 'prazo_entrega', 'painel_resumo_estoque', 'botao_lista_compras', 'btn_whatsapp')
    list_filter = ('status', 'prazo_entrega')
    search_fields = ('cliente__nome', 'id')

    readonly_fields = (
        'painel_compras_detalhado',
        'readonly_preco_sugerido',
        'readonly_preco_minimo',
        'readonly_status_viabilidade',
        'readonly_simulacao_pgto',
        'readonly_restante',
        'readonly_botao_orcamento',
        'readonly_botao_contrato'
    )

    fieldsets = (
        ('1. Comercial e Prazos', {
            'fields': ('cliente', 'status', 'prazo_entrega', 'observacoes')
        }),
        ('2. Parâmetros de Custo (Preencha para calcular)', {
            'fields': (('horas_estimadas', 'custo_transporte'),)
        }),
        ('3. Valores e Negociação', {
            'fields': (
                ('quantidade', 'preco_manual_referencia', 'percentual_desconto'),
                ('valor_total', 'valor_sinal'),
                ('qtd_parcelas', 'dias_intervalo'),
                'autorizado_gerencia'
            )
        }),
        ('4. SUPRIMENTOS (Roteiro de Compra)', {
            'fields': ('painel_compras_detalhado',),
            'description': 'O sistema verifica automaticamente se há material para produzir.'
        }),
        ('5. Cockpit de Custos (Simulação em Tempo Real)', {
            'fields': (
                'readonly_preco_sugerido',
                'readonly_preco_minimo',
                'readonly_status_viabilidade',
                'readonly_simulacao_pgto',
                'readonly_restante',
                ('readonly_botao_orcamento', 'readonly_botao_contrato')
            )
        })
    )

    def save_model(self, request, obj, form, change):
        if obj.status == 'APROVADO' and 'status' in form.changed_data:
            super().save_model(request, obj, form, change)
            PedidoService.aprovar_pedido(obj, user=request.user)
        elif obj.status == 'CONFEC' and 'status' in form.changed_data:
            try:
                PedidoService.iniciar_confeccao(obj, user=request.user)
            except ValueError as e:
                from django.contrib import messages
                messages.error(request, str(e))
        else:
            super().save_model(request, obj, form, change)

    def painel_compras_detalhado(self, obj):
        if not hasattr(obj, 'ficha_tecnica'): return "Salve o pedido e crie a ficha técnica primeiro."
        faltantes = obj.gerar_roteiro_compras()
        if not faltantes:
            return mark_safe(
                '<div style="background:#d4edda; color:#155724; padding:15px; border-radius:5px; border: 1px solid #c3e6cb;">'
                '✅ <strong>ESTOQUE OK!</strong> Todos os materiais estão disponíveis.<br>'
                'Você pode mudar o status para <strong>EM CONFECÇÃO</strong>.'
                '</div>'
            )
        html = '<div style="background:#f8d7da; color:#721c24; padding:15px; border-radius:5px; border: 1px solid #f5c6cb;">'
        html += '⚠️ <strong>NECESSÁRIO COMPRAR MATERIAIS:</strong><ul style="margin-top:10px; margin-left: 20px;">'
        for i in faltantes:
            html += f'<li>🔴 <strong>{i["material"]}</strong>: Falta {i["falta_comprar"]:.2f} {i["unidade"]}</li>'
        html += '</ul><br>👉 <em>Realize a compra (Movimentação de Estoque) antes de iniciar a produção.</em></div>'
        return mark_safe(html)

    def painel_resumo_estoque(self, obj):
        if obj.status == 'ORCAMENTO': return "-"
        if obj.gerar_roteiro_compras(): return mark_safe('<span style="color:red; font-weight:bold">🔴 Falta Material</span>')
        return mark_safe('<span style="color:green; font-weight:bold">🟢 Estoque OK</span>')

    def status_badge(self, obj):
        colors = {'ORCAMENTO':'gray', 'APROVADO':'blue', 'COMPRA':'orange', 'CONFEC':'#6f42c1', 'PROVA':'purple', 'ENTREGUE':'green', 'CANCELADO': 'red'}
        return format_html(
            '<span style="background:{}; color:white; padding:2px 6px; border-radius:10px; font-weight:bold; font-size:11px;">{}</span>',
            colors.get(obj.status, 'gray'),
            obj.get_status_display()
        )

    def btn_whatsapp(self, obj):
        if not obj.cliente.telefone: return "-"
        url = gerar_link_whatsapp(obj.cliente.telefone, "Olá " + obj.cliente.nome)
        return format_html('<a class="button" style="background-color:#25D366; color:white" href="{}" target="_blank">📱 Zap</a>', url)

    def botao_lista_compras(self, obj):
        if obj.status in ['ORCAMENTO', 'CANCELADO', 'ENTREGUE']: return "-"
        faltantes = obj.gerar_roteiro_compras()
        style = "background:#d35400; color:white;" if faltantes else "background:#eee; color:#555;"
        text = "🛒 Lista Compras" if faltantes else "📄 Lista (OK)"
        url = reverse('lista_compras_pdf', args=[obj.id])
        return format_html('<a class="button" href="{}" target="_blank" style="{}">{}</a>', url, style, text)

    def readonly_preco_sugerido(self, obj): return "Aguardando cálculo..."
    readonly_preco_sugerido.short_description = "Preço Tabela (Sugerido)"

    def readonly_preco_minimo(self, obj): return "Aguardando cálculo..."
    readonly_preco_minimo.short_description = "Preço Mínimo (Break-Even)"

    def readonly_status_viabilidade(self, obj): return mark_safe("<span style='color:#777; font-style:italic;'>Preencha os valores para ver a DRE...</span>")
    readonly_status_viabilidade.short_description = "DRE do Lote (Diagnóstico)"

    def readonly_simulacao_pgto(self, obj): return "Aguardando dados..."
    readonly_simulacao_pgto.short_description = "Simulação de Pagamento"

    def readonly_restante(self, obj): return "Aguardando dados..."
    readonly_restante.short_description = "Restante na Entrega"

    def readonly_botao_orcamento(self, obj):
        if not obj.pk: return ""
        url = reverse('gerar_orcamento', args=[obj.id])
        return mark_safe(f'<a href="{url}" id="btn_gerar_pdf_orcamento" class="button" target="_blank" style="background:#2563eb; color:white; font-weight:bold; padding: 8px 16px; border-radius: 4px; display: inline-block; margin-right:10px;"><i class="fas fa-file-pdf"></i> 🖨️ Gerar PDF do Orçamento</a>')
    readonly_botao_orcamento.short_description = "Documento Proposta"

    def readonly_botao_contrato(self, obj):
        if not obj.pk: return ""
        if obj.status == 'ORCAMENTO':
            return mark_safe("<span style='color:#999; font-style:italic; line-height:30px;'>⚠️ Contrato disponível após a aprovação comercial.</span>")
        try:
            url = reverse('gerar_contrato', args=[obj.id])
        except:
            url = f"/juridico/contrato/{obj.id}/"
        return mark_safe(f'<a href="{url}" class="button" target="_blank" style="background:#10b981; color:white; font-weight:bold; padding: 8px 16px; border-radius: 4px; display: inline-block;"><i class="fas fa-gavel"></i> 📄 🖨️ Emitir Contrato Formal</a>')
    readonly_botao_contrato.short_description = "Instrumento Jurídico"

    class Media:
        js = ('js/admin_simulador_vendas.js',)

# --- CADASTRO DE MATERIAIS E ESTOQUE ---
@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = ('nome', 'preco_custo', 'unidade', 'estoque_atual')
    search_fields = ('nome',)  # <-- É essa linha que o autocomplete exige!

# Certifique-se de que os outros modelos também estão registrados no final:
admin.site.register(MovimentacaoEstoque)
admin.site.register(ParametrosSistema)
admin.site.register(TemplateMedida)
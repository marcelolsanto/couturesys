# producao/views.py
from core.models import Cliente
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q
from .forms import PedidoForm
from .services import PedidoService
from django.http import JsonResponse
from decimal import Decimal
from django.views.decorators.http import require_http_methods
from .models import Pedido, ParametrosSistema
import traceback
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
from django.utils import timezone

@require_http_methods(["GET"])
def calcular_previa_avancada(request):
    try:
        # --- FUNÇÃO DE LIMPEZA BLINDADA ---
        def limpar_moeda(valor):
            if not valor or valor == 'null' or valor == 'None': return Decimal('0')
            valor_str = str(valor).replace('R$', '').strip()
            if not valor_str: return Decimal('0')
            try:
                return Decimal(valor_str)
            except:
                valor_br = valor_str.replace('.', '').replace(',', '.')
                try:
                    return Decimal(valor_br)
                except:
                    return Decimal('0')

        # --- 1. RECEBE DADOS ---
        pedido_id = request.GET.get('pedido_id')

        try:
            q_val = request.GET.get('qtd', '1')
            qtd_pecas = int(float(q_val))
            if qtd_pecas < 1: qtd_pecas = 1
        except:
            qtd_pecas = 1

        horas_unit = limpar_moeda(request.GET.get('horas'))
        frete_unit = limpar_moeda(request.GET.get('frete'))
        sinal = limpar_moeda(request.GET.get('sinal'))
        desconto_pct = limpar_moeda(request.GET.get('desconto'))
        preco_manual_unit = limpar_moeda(request.GET.get('manual'))

        # --- 2. OBTENÇÃO DOS PARÂMETROS DE CUSTO (CORREÇÃO AQUI) ---
        # Inicializa variáveis
        custo_hora_ref = Decimal('0')
        custo_fixo_mensal_ref = Decimal('0')
        meta_clientes_ref = Decimal('1')  # Evita divisão por zero
        taxa_imposto_ref = Decimal('0')
        margem_lucro_ref = Decimal('0')

        custo_materiais_unit = Decimal('0.00')
        ficha_encontrada = False

        # Cenário A: Pedido Existente (Usa Snapshot ou Config Atual)
        if pedido_id and pedido_id not in ['None', 'null', '']:
            try:
                pedido = Pedido.objects.get(pk=pedido_id)
                # Acessa as properties da INSTÂNCIA (pedido.CUSTO_HORA), não da Classe
                custo_hora_ref = pedido.CUSTO_HORA
                custo_fixo_mensal_ref = pedido.CUSTO_FIXO_MENSAL
                meta_clientes_ref = pedido.META_CLIENTES
                taxa_imposto_ref = pedido.TAXA_IMPOSTO
                margem_lucro_ref = pedido.MARGEM_LUCRO

                if hasattr(pedido, 'ficha_tecnica'):
                    ficha_encontrada = True
                    custo_materiais_unit = sum(
                        item.custo_calculado for item in pedido.ficha_tecnica.materiais_usados.all())
            except:
                # Fallback se der erro ao buscar
                config = ParametrosSistema.get_solo()
                custo_hora_ref = config.custo_hora_padrao
                custo_fixo_mensal_ref = config.custo_fixo_mensal
                meta_clientes_ref = config.meta_clientes_mes
                taxa_imposto_ref = config.taxa_imposto_padrao
                margem_lucro_ref = config.margem_lucro_meta

        # Cenário B: Simulação Nova (Usa Configuração Global Direta)
        else:
            config = ParametrosSistema.get_solo()
            custo_hora_ref = config.custo_hora_padrao
            custo_fixo_mensal_ref = config.custo_fixo_mensal
            meta_clientes_ref = config.meta_clientes_mes
            taxa_imposto_ref = config.taxa_imposto_padrao
            margem_lucro_ref = config.margem_lucro_meta

        # --- 3. CÁLCULOS ---
        # Rateio Unitário
        rateio_unit = custo_fixo_mensal_ref / meta_clientes_ref if meta_clientes_ref > 0 else 0

        custo_mo_unit = horas_unit * custo_hora_ref
        custo_op_unit = custo_mo_unit + frete_unit + rateio_unit + custo_materiais_unit

        # --- 4. ESCALA DO LOTE ---
        custo_op_total_lote = custo_op_unit * qtd_pecas

        # --- 5. PRECIFICAÇÃO ---
        divisor_meta = max(Decimal('1.00') - (margem_lucro_ref + taxa_imposto_ref), Decimal('0.1'))
        preco_sugerido_total = (custo_op_total_lote / divisor_meta).quantize(Decimal('0.01'))

        if preco_manual_unit > 0:
            preco_base_total = preco_manual_unit * qtd_pecas
        else:
            preco_base_total = preco_sugerido_total

        valor_desconto = preco_base_total * (desconto_pct / Decimal('100'))
        receita_liquida_total = max(preco_base_total - valor_desconto, Decimal('0.00'))

        # --- 6. DRE ---
        valor_imposto_total = receita_liquida_total * taxa_imposto_ref
        lucro_liquido_total = receita_liquida_total - valor_imposto_total - custo_op_total_lote

        margem_real_pct = Decimal('0')
        if receita_liquida_total > 0:
            margem_real_pct = (lucro_liquido_total / receita_liquida_total) * 100

        # --- 7. HTML ---
        def fmt(v):
            return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

        # Status Code e Cores
        if lucro_liquido_total < 0:
            cor, bg, icone, msg = "#721c24", "#f8d7da", "⛔", f"PREJUÍZO NO LOTE ({qtd_pecas} pçs)"
            status_code = 'critico'
        elif margem_real_pct < (margem_lucro_ref * 100):
            cor, bg, icone, msg = "#856404", "#fff3cd", "⚠️", f"Margem Baixa ({margem_real_pct:.1f}%)"
            status_code = 'alerta'
        else:
            cor, bg, icone, msg = "#155724", "#d4edda", "✅", f"Lucro Excelente ({margem_real_pct:.1f}%)"
            status_code = 'ok'

        aviso_materiais = ""
        if not ficha_encontrada:
            aviso_materiais = "<br><small style='color:orange'>(!) Ficha Técnica não encontrada.</small>"
        elif custo_materiais_unit == 0:
            aviso_materiais = "<br><small style='color:red'>(!) Materiais R$ 0,00.</small>"

        html_dre = f"""
        <div style="background-color:{bg}; color:{cor}; padding:10px; border-radius:5px; border:1px solid {cor};">
            <strong style="font-size:13px;">{icone} {msg}</strong>
            <hr style="margin:5px 0; opacity:0.3;">
            <table style="width:100%; font-size:11px;">
                <tr><td colspan="2"><strong>Lote: {qtd_pecas} unidades</strong></td></tr>
                <tr><td>(+) Venda Total:</td><td align="right">{fmt(receita_liquida_total)}</td></tr>
                <tr><td>(-) Impostos:</td><td align="right" style="color:red">{fmt(valor_imposto_total)}</td></tr>
                <tr><td>(-) Custos Totais:</td><td align="right" style="color:red">{fmt(custo_op_total_lote)}</td></tr>
                <tr style="font-weight:bold; border-top:1px solid {cor}">
                    <td>(=) LUCRO LOTE:</td><td align="right">{fmt(lucro_liquido_total)}</td>
                </tr>
            </table>
            <div style="font-size:10px; margin-top:5px; text-align:right">
                Unitário Médio: {fmt(receita_liquida_total / qtd_pecas) if qtd_pecas else 0}
            </div>
            {aviso_materiais}
        </div>
        """

        preco_equilibrio_total = (custo_op_total_lote / (Decimal('1') - taxa_imposto_ref)).quantize(Decimal('0.01'))
        restante = max(receita_liquida_total - sinal, Decimal('0.00'))

        return JsonResponse({
            'preco_sugerido': fmt(preco_sugerido_total),
            'preco_minimo': fmt(preco_equilibrio_total),
            'preco_final_fmt': fmt(receita_liquida_total),
            'preco_final_raw': str(receita_liquida_total),
            'restante': fmt(restante),
            'html_diagnostico': html_dre,
            'status_code': status_code,
            'simulacao': {
                'a_vista': fmt(receita_liquida_total * Decimal('0.95')),
                'parcela_3x': fmt(receita_liquida_total / 3)
            }
        })

    except Exception as e:
        print("ERRO API:", traceback.format_exc())
        return JsonResponse({'erro': str(e)}, status=400)


def gerar_lista_compras_pdf(request, pedido_id):
    pedido = get_object_or_404(Pedido, pk=pedido_id)

    # Usa a inteligência do modelo para pegar só o que falta
    itens_faltantes = pedido.gerar_roteiro_compras()

    context = {
        'pedido': pedido,
        'itens': itens_faltantes,
        'data_emissao': timezone.now()
    }

    # Vamos criar este template simples abaixo
    template_path = 'producao/lista_compras_pdf.html'
    template = get_template(template_path)
    html = template.render(context)

    response = HttpResponse(content_type='application/pdf')
    filename = f"Lista_Compras_Ped_{pedido.id}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse('Erro ao gerar PDF')
    return response


# 1. LISTAR (Read)
def lista_pedidos(request):
    busca = request.GET.get('q')
    filtro_status = request.GET.get('status')

    pedidos = Pedido.objects.all().order_by('-id')

    if busca:
        pedidos = pedidos.filter(
            Q(cliente__nome__icontains=busca) | Q(id__icontains=busca)
        )

    if filtro_status:
        pedidos = pedidos.filter(status=filtro_status)

    return render(request, 'producao/lista_pedidos.html', {'pedidos': pedidos[:50]})


# 2. NOVO / EDITAR (Create / Update)
def gerenciar_pedido(request, id=None):
    if id:
        pedido = get_object_or_404(Pedido, pk=id)
        titulo = f"Editar Pedido #{id}"
    else:
        pedido = None
        titulo = "Novo Pedido"

    # Adicione isso para pegar a configuração global
    config = ParametrosSistema.get_solo()

    # --- LÓGICA DE PESQUISA DE CLIENTES ---
    search_query = request.GET.get('q')
    clientes = []

    # Só busca se houver algo digitado (para não pesar a página)
    if search_query:
        clientes = Cliente.objects.filter(
            Q(nome__icontains=search_query) | Q(cpf__icontains=search_query)
        )[:10]  # Limita a 10 resultados para não quebrar o layout

    if request.method == 'POST':
        form = PedidoForm(request.POST, instance=pedido)
        if form.is_valid():
            # Salva o objeto básico primeiro
            obj = form.save(commit=False)
            obj.save()  # Salva para ter ID

            # --- INTEGRAÇÃO COM SERVICE LAYER ---
            # Se o usuário marcou APROVADO no formulário, rodamos a lógica financeira
            if obj.status == 'APROVADO':
                PedidoService.aprovar_pedido(obj, user=request.user)
            # ------------------------------------

            messages.success(request, "✅ Pedido salvo com sucesso!")
            return redirect('lista_pedidos')
    else:
        form = PedidoForm(instance=pedido)

        context = {
            'form': form,
            'titulo': titulo,
            'clientes': clientes,  # Passamos a lista filtrada
            'search_query': search_query,  # Para manter o texto no input
            'custo_hora': Decimal(config.custo_hora_padrao),
            'taxa_imposto': Decimal(config.taxa_imposto_padrao)
        }

    return render(request, 'producao/form_pedido.html', {'form': form, 'titulo': titulo})


# 3. EXCLUIR (Delete)
def excluir_pedido(request, id):
    pedido = get_object_or_404(Pedido, pk=id)

    if request.method == 'POST':
        try:
            pedido.delete()
            messages.warning(request, "🗑️ Pedido removido.")
        except Exception as e:
            messages.error(request, "⛔ Não foi possível excluir (pode ter financeiro vinculado).")

        return redirect('lista_pedidos')

    return render(request, 'producao/confirmar_exclusao.html', {'pedido': pedido})
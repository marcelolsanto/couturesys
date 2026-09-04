from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
from decimal import Decimal
from django.utils import timezone
from producao.models import Pedido


def fmt(valor):
    if valor is None: valor = 0
    try:
        if isinstance(valor, str):
            valor = Decimal(valor.replace('R$', '').replace('.', '').replace(',', '.'))
        return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "R$ 0,00"


def gerar_orcamento_pdf(request, pedido_id):
    pedido = get_object_or_404(Pedido, pk=pedido_id)

    if 'horas' in request.GET:
        try:
            def limpar(v):
                if not v or v == 'null': return Decimal('0')
                return Decimal(str(v).replace('R$', '').replace('.', '').replace(',', '.').strip())

            pedido.quantidade = int(float(request.GET.get('qtd', pedido.quantidade)))
            pedido.horas_estimadas = limpar(request.GET.get('horas'))
            pedido.custo_transporte = limpar(request.GET.get('frete'))
            pedido.valor_sinal = limpar(request.GET.get('sinal'))
            pedido.percentual_desconto = limpar(request.GET.get('desconto'))

            preco_manual = limpar(request.GET.get('manual'))
            if preco_manual > 0:
                pedido.preco_manual_referencia = preco_manual
                base_total = preco_manual * pedido.quantidade
            else:
                base_total = pedido.calcular_preco_sugerido()

            valor_desc = base_total * (pedido.percentual_desconto / Decimal('100'))
            pedido.valor_total = base_total - valor_desc
        except Exception as e:
            print(f"Erro no override do PDF: {e}")

    qtd = pedido.quantidade
    CUSTO_HORA = pedido.CUSTO_HORA
    RATEIO_UNIT = pedido.CUSTO_FIXO_MENSAL / pedido.META_CLIENTES if pedido.META_CLIENTES > 0 else 0

    custo_mo_total = (pedido.horas_estimadas * CUSTO_HORA) * qtd
    custo_trans_total = pedido.custo_transporte * qtd
    custo_fixo_total = RATEIO_UNIT * qtd

    custo_mat_total = Decimal('0.00')
    lista_materiais = []

    if hasattr(pedido, 'ficha_tecnica') and pedido.ficha_tecnica.pk:
        for item in pedido.ficha_tecnica.materiais_usados.all():
            item_total = {
                'nome': item.material.nome,
                'unidade': item.material.unidade,
                'qtd_unitaria': f"{item.quantidade:,.2f}".replace('.', ','),
                'qtd_total_lote': f"{item.quantidade * qtd:,.2f}".replace('.', ','),
                'custo_total_item': fmt(item.custo_calculado * qtd)
            }
            lista_materiais.append(item_total)
            custo_mat_total += item.custo_calculado * qtd

    custo_operacional_total = custo_mo_total + custo_trans_total + custo_mat_total + custo_fixo_total
    valor_final_venda = pedido.valor_total
    restante_pagar = max(valor_final_venda - pedido.valor_sinal, Decimal('0.00'))

    context = {
        'pedido': pedido,
        'cliente': pedido.cliente,
        'itens_materiais': lista_materiais,
        'custo_mo': fmt(custo_mo_total),
        'custo_trans': fmt(custo_trans_total),
        'custo_fixo': fmt(custo_fixo_total),
        'custo_operacional_total': fmt(custo_operacional_total),
        'valor_final_orcamento': fmt(valor_final_venda),
        'sinal_pago': fmt(pedido.valor_sinal),
        'restante_pagar': fmt(restante_pagar),
        'qtd_lote': qtd
    }

    template = get_template('juridico/orcamento_pdf.html')
    html = template.render(context)
    response = HttpResponse(content_type='application/pdf')
    filename = f"Orcamento_{pedido.id}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err: return HttpResponse('Erro PDF')
    return response


def gerar_contrato_pdf(request, pedido_id):
    pedido = get_object_or_404(Pedido, pk=pedido_id)
    preco_medio = pedido.valor_total / pedido.quantidade if pedido.quantidade > 0 else 0
    restante = pedido.valor_total - pedido.valor_sinal

    context = {
        'pedido': pedido,
        'cliente': pedido.cliente,
        'data_emissao': timezone.now().date(),
        'nome_atelier': 'CoutureSys Atelier',
        'qtd_pecas': pedido.quantidade,
        'valor_total_contrato': fmt(pedido.valor_total),
        'sinal_pago': fmt(pedido.valor_sinal),
        'restante_pagar': fmt(restante),
        'preco_unitario_medio': fmt(preco_medio),
    }

    template = get_template('juridico/contrato_pdf.html')
    html = template.render(context)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Contrato_{pedido.id}.pdf"'
    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err: return HttpResponse('Erro PDF')
    return response
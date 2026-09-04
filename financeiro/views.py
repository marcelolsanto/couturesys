# financeiro/views.py
from django.shortcuts import render, get_object_or_404
from producao.models import Pedido, ParametrosSistema
import json
from django.http import HttpResponse
from django.template.loader import get_template
from django.utils import timezone
from xhtml2pdf import pisa
from django.db.models import Sum
from django.db.models.functions import TruncDay
from decimal import Decimal
from django.contrib.admin.views.decorators import staff_member_required
from .models import ContaPagar, ContaReceber

@staff_member_required
def dashboard(request):
    # Função auxiliar de formatação moeda BR
    def fmt(v):
        if v is None: v = Decimal('0.00')
        return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    # ==========================================
    # PARTE 1: FINANCEIRO REAL (Fluxo de Caixa)
    # Baseado no que realmente entrou e saiu do banco (Contas a Pagar/Receber)
    # ==========================================

    # Entradas (Status = PAGO)
    receita_total = ContaReceber.objects.filter(status='PAGO').aggregate(Sum('valor'))['valor__sum'] or Decimal('0.00')

    # Saídas (Status = PAGO)
    despesa_total = ContaPagar.objects.filter(status='PAGO').aggregate(Sum('valor'))['valor__sum'] or Decimal('0.00')

    # Saldo
    saldo_real = receita_total - despesa_total

    # Previsões (Status = PENDENTE)
    a_receber = ContaReceber.objects.filter(status='PENDENTE').aggregate(Sum('valor'))['valor__sum'] or Decimal('0.00')
    a_pagar = ContaPagar.objects.filter(status='PENDENTE').aggregate(Sum('valor'))['valor__sum'] or Decimal('0.00')

    # ==========================================
    # PARTE 2: OPERACIONAL (Produção Teórica)
    # Baseado nos Pedidos e Fichas Técnicas (DRE Gerencial)
    # ==========================================

    pedidos_ativos = Pedido.objects.filter(status__in=['APROVADO', 'CONFEC', 'PROVA', 'ENTREGUE'])

    total_faturamento = Decimal('0.00')
    total_impostos = Decimal('0.00')
    total_materiais = Decimal('0.00')
    total_mao_obra = Decimal('0.00')
    total_frete = Decimal('0.00')
    total_fixo = Decimal('0.00')

    for p in pedidos_ativos:
        qtd = p.quantidade
        total_faturamento += p.valor_total

        # Custos baseados nos snapshots do pedido
        total_impostos += p.valor_total * p.TAXA_IMPOSTO
        total_mao_obra += (p.horas_estimadas * p.CUSTO_HORA) * qtd
        total_frete += p.custo_transporte * qtd

        # Custo de Material (via Ficha Técnica)
        custo_mat_unit = Decimal('0.00')
        if hasattr(p, 'ficha_tecnica'):
            custo_mat_unit = sum(item.custo_calculado for item in p.ficha_tecnica.materiais_usados.all())
        total_materiais += custo_mat_unit * qtd

        # Rateio Fixo
        rateio_unit = Decimal('0.00')
        if p.META_CLIENTES > 0:
            rateio_unit = p.CUSTO_FIXO_MENSAL / p.META_CLIENTES
        total_fixo += rateio_unit * qtd

    custos_operacionais = total_materiais + total_mao_obra + total_frete + total_fixo
    lucro_operacional = total_faturamento - total_impostos - custos_operacionais
    custos_totais_com_imposto = custos_operacionais + total_impostos

    margem_pct = 0
    if total_faturamento > 0:
        margem_pct = (lucro_operacional / total_faturamento) * 100

    # --- DADOS DO GRÁFICO (Diário) ---
    # Aqui usamos as Vendas (Pedidos) como base para o gráfico,
    # mas poderíamos usar o ContaReceber se quiséssemos fluxo de caixa real no gráfico.
    vendas_diarias = pedidos_ativos.annotate(dia=TruncDay('data_pedido')).values('dia').annotate(
        total=Sum('valor_total')).order_by('dia')
    grafico_labels = []
    grafico_data = []
    for venda in vendas_diarias:
        if venda['dia']:
            grafico_labels.append(venda['dia'].strftime('%d/%m'))
            grafico_data.append(Decimal(venda['total']))

    # Se não tiver dados, coloca um dummy para o gráfico não quebrar
    if not grafico_labels:
        grafico_labels = ["Hoje"]
        grafico_data = [0]

    # ==========================================
    # CONTEXTO FINAL (Enviando tudo para o HTML)
    # ==========================================
    context = {
        # --- DADOS REAIS (CAIXA) ---
        'saldo_real': fmt(saldo_real),
        'receita_real': fmt(receita_total),
        'despesa_real': fmt(despesa_total),
        'previsao_entrada': fmt(a_receber),
        'previsao_saida': fmt(a_pagar),

        # --- DADOS OPERACIONAIS (PEDIDOS) ---
        'qtd_pedidos': pedidos_ativos.count(),
        'total_faturamento': fmt(total_faturamento),
        'custos_totais': fmt(custos_totais_com_imposto),
        'lucro_liquido': fmt(lucro_operacional),
        'margem_real_pct': margem_pct,

        # Detalhamento de Custos
        'detalhe_materiais': fmt(total_materiais),
        'detalhe_mo': fmt(total_mao_obra),
        'detalhe_impostos': fmt(total_impostos),
        'detalhe_frete': fmt(total_frete),
        'detalhe_fixo': fmt(total_fixo),

        # Gráfico
        'grafico_labels': grafico_labels,
        'grafico_data': [float(v) for v in grafico_data],
    }

    return render(request, 'financeiro/dashboard.html', context)


def simulador_pagamento(request):
    if request.method == 'GET':
        # Pega parâmetros globais (Custo Hora, Impostos)
        config = ParametrosSistema.get_solo()
        pedidos = Pedido.objects.exclude(status='ENTREGUE').order_by('-id')

        pedidos_data = []

        for p in pedidos:
            # 1. CUSTO DE MATERIAIS (TECIDO/AVIAMENTOS)
            custo_materiais = Decimal('0.00')
            materiais_alertas = []  # Lista para avisar se falta estoque

            if hasattr(p, 'ficha_tecnica'):
                for item in p.ficha_tecnica.materiais_usados.all():
                    qtd_necessaria = item.quantidade * p.quantidade
                    custo_item = qtd_necessaria * item.material.preco_custo
                    custo_materiais += custo_item

                    # Verificação de Estoque
                    if item.material.estoque_atual < qtd_necessaria:
                        falta = qtd_necessaria - item.material.estoque_atual
                        materiais_alertas.append(f"Falta {falta} {item.material.unidade} de {item.material.nome}")

            # 2. CUSTO DE SERVIÇO (MÃO DE OBRA)
            # Se tiver ficha técnica com tempo, usa ela. Senão, estima.
            horas_estimadas = Decimal('0.00')
            if hasattr(p, 'ficha_tecnica') and p.ficha_tecnica.tempo_estimado_horas:
                horas_estimadas = p.ficha_tecnica.tempo_estimado_horas * p.quantidade
            else:
                # Fallback: Estima baseado no valor (apenas para não zerar)
                horas_estimadas = Decimal('5.0')

            # Usa custo_hora_calculado (property correta de ParametrosSistema)
            custo_mao_obra = horas_estimadas * config.custo_hora_calculado

            # 3. CUSTOS OPERACIONAIS & TAXAS
            # Taxa Adm (Ex: 15% sobre custos diretos)
            taxa_admin_pct = Decimal('0.15')
            valor_taxa_admin = (custo_materiais + custo_mao_obra) * taxa_admin_pct

            # Impostos (Ex: 6% sobre o preço de venda SUGERIDO)
            imposto_pct = config.taxa_imposto_padrao
            valor_impostos = p.valor_total * imposto_pct

            # Frete
            custo_frete = getattr(p, 'custo_transporte', Decimal('0.00'))

            # 4. PONTO DE EQUILÍBRIO (BREAK-EVEN)
            # Quanto custa para produzir (sem lucro zero)
            ponto_equilibrio = custo_materiais + custo_mao_obra + valor_taxa_admin + valor_impostos + custo_frete

            pedidos_data.append({
                'id': p.id,
                'cliente': p.cliente.nome,
                'produto': f"{p.quantidade}x Peças",
                'preco_tabela': Decimal(p.valor_total),
                # Custos detalhados para o gráfico
                'custo_mat': Decimal(custo_materiais),
                'custo_mo': Decimal(custo_mao_obra),
                'custo_frete': Decimal(custo_frete),
                'custo_taxas': Decimal(valor_taxa_admin + valor_impostos),
                'ponto_equilibrio': Decimal(ponto_equilibrio),
                'alertas_estoque': materiais_alertas
            })

        # Serializa para JSON para o JavaScript ler fácil
        pedidos_json = json.dumps(pedidos_data)

        return render(request, 'financeiro/simulador.html', {
            'pedidos': pedidos,
            'pedidos_json': pedidos_json
        })

    # POST: Processa, Salva e Gera PDF
    if request.method == 'POST':
        pedido_id = request.POST.get('pedido_id')
        metodo = request.POST.get('metodo_selecionado')
        condicao_texto = request.POST.get('resumo_condicoes')  # Ex: "10x de R$ 150,00"
        valor_final = request.POST.get('valor_final_hidden')

        # 1. Recupera e Atualiza o Pedido
        pedido = get_object_or_404(Pedido, pk=pedido_id)

        # Registra a simulação no histórico do pedido
        timestamp = timezone.now().strftime("%d/%m/%Y às %H:%M")
        registro_historico = (
            f"\n--- SIMULAÇÃO DE PAGAMENTO ({timestamp}) ---\n"
            f"Método: {metodo}\n"
            f"Condição: {condicao_texto}\n"
            f"Valor Simulado: R$ {valor_final}\n"
        )

        if pedido.observacoes:
            pedido.observacoes += registro_historico
        else:
            pedido.observacoes = registro_historico

        pedido.save()

        # 2. Prepara dados para o PDF
        context = {
            'pedido': pedido,
            'cliente': pedido.cliente,
            'metodo': metodo,
            'condicao': condicao_texto,
            'valor_final': valor_final,
            'data_emissao': timezone.now()
        }

        # 3. Gera o PDF
        template_path = 'financeiro/pdf_orcamento.html'
        template = get_template(template_path)
        html = template.render(context)

        response = HttpResponse(content_type='application/pdf')
        filename = f"Orcamento_Pedido_{pedido.id}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        pisa_status = pisa.CreatePDF(html, dest=response)
        if pisa_status.err:
            return HttpResponse('Erro ao gerar PDF')

        return response
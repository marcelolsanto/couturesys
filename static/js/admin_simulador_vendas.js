document.addEventListener("DOMContentLoaded", function() {

    const form = document.getElementById("pedido_form");
    const inputs = {
        qtd: document.getElementById("id_quantidade"),
        horas: document.getElementById("id_horas_estimadas"),
        frete: document.getElementById("id_custo_transporte"),
        sinal: document.getElementById("id_valor_sinal"),
        desconto: document.getElementById("id_percentual_desconto"),
        manual: document.getElementById("id_preco_manual_referencia"),
        totalFinalInput: document.getElementById("id_valor_total"),
        autorizacao: document.getElementById("id_autorizado_gerencia")
    };

    const displays = {
        sugerido: document.querySelector(".field-readonly_preco_sugerido .readonly"),
        minimo: document.querySelector(".field-readonly_preco_minimo .readonly"),
        statusContainer: document.querySelector(".field-readonly_status_viabilidade .readonly"),
        simulacao: document.querySelector(".field-readonly_simulacao_pgto .readonly"),
        restante: document.querySelector(".field-readonly_restante .readonly")
    };

    let estadoAtualVenda = { status: 'ok' };

    const urlPath = window.location.pathname;
    const match = urlPath.match(/\/pedido\/(\d+)\/change/);
    const pedidoId = match ? match[1] : null;

    function getRaw(el) { return el ? el.value : '0'; }

    function calcular() {
        if (!inputs.horas) return;

        const params = new URLSearchParams({
            pedido_id: pedidoId,
            qtd: getRaw(inputs.qtd) || '1',
            horas: getRaw(inputs.horas),
            frete: getRaw(inputs.frete),
            sinal: getRaw(inputs.sinal),
            desconto: getRaw(inputs.desconto),
            manual: getRaw(inputs.manual)
        });

        const btnPdf = document.getElementById("btn_gerar_pdf_orcamento");
        if (btnPdf && pedidoId) {
            btnPdf.href = `/juridico/orcamento/${pedidoId}/?${params.toString()}`;
        }

        fetch(`/producao/api/calcular-pedido-avancado/?${params.toString()}`)
            .then(res => res.json())
            .then(data => {
                if(data.erro) return;

                if(displays.sugerido) displays.sugerido.innerText = data.preco_sugerido;
                if(displays.minimo) displays.minimo.innerText = data.preco_minimo;
                if(displays.restante) displays.restante.innerText = data.restante;

                if(inputs.totalFinalInput && inputs.totalFinalInput.dataset.manualEdit !== 'true') {
                    inputs.totalFinalInput.value = data.preco_final_raw;
                }

                if(displays.statusContainer) displays.statusContainer.innerHTML = data.html_diagnostico;

                if(displays.simulacao) {
                    displays.simulacao.innerHTML = `
                        <div style="font-size:13px; color:#555;">
                            Resumo do Lote:<br>
                            PIX à vista: <strong style="color: green;">${data.simulacao.a_vista}</strong><br>
                            Cartão 3x: <strong>${data.simulacao.parcela_3x} / mês</strong>
                        </div>
                    `;
                }

                estadoAtualVenda.status = data.status_code;
            })
            .catch(err => console.error("Erro Fetch:", err));
    }

    const allInputs = [inputs.qtd, inputs.horas, inputs.frete, inputs.sinal, inputs.desconto, inputs.manual];
    allInputs.forEach(el => {
        if(el) {
            el.addEventListener('input', () => setTimeout(calcular, 300));
            el.addEventListener('change', calcular);
        }
    });

    if(inputs.totalFinalInput) {
        inputs.totalFinalInput.addEventListener('input', function() {
            this.dataset.manualEdit = 'true';
        });
    }

    if (form) {
        form.addEventListener('submit', function(e) {
            const statusPedido = document.getElementById("id_status").value;
            if (statusPedido !== 'ORCAMENTO') {
                if (estadoAtualVenda.status === 'critico') {
                    e.preventDefault();
                    alert("⛔ AÇÃO BLOQUEADA!\n\nEste pedido está gerando PREJUÍZO financeiro.");
                    return false;
                }
            }
        });
    }

    setTimeout(calcular, 500);
});
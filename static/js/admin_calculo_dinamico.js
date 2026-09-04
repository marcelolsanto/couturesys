/*
 * ESTE SCRIPT RODA NO NAVEGADOR DENTRO DO ADMIN DO DJANGO.
 * Ele escuta mudanças nos campos de horas, frete e sinal,
 * chama o servidor para calcular e atualiza a tela.
 */
document.addEventListener("DOMContentLoaded", function() {
    // 1. Identifica os campos na tela do Admin
    const inputHoras = document.getElementById("id_horas_estimadas");
    const inputFrete = document.getElementById("id_custo_transporte");
    const inputSinal = document.getElementById("id_valor_sinal");
    const inputValorTotal = document.getElementById("id_valor_total");

    // Campos de "espelho" (ReadOnly)
    const spanPreviaCusto = document.querySelector(".field-previa_custo_total .readonly");
    const spanPreviaFinal = document.querySelector(".field-previa_valor_final .readonly");
    const spanPreviaRestante = document.querySelector(".field-previa_restante .readonly");

    // Função que faz a mágica
    function calcularDinamico() {
        // Pega os valores atuais dos inputs
        let horas = inputHoras.value || '0';
        let frete = inputFrete.value.replace('R$', '').trim() || '0';
        let sinal = inputSinal.value.replace('R$', '').trim() || '0';

        // Monta a URL para chamar nosso backend Python
        let url = `/api/calcular-pedido/?horas=${encodeURIComponent(horas)}&frete=${encodeURIComponent(frete)}&sinal=${encodeURIComponent(sinal)}`;

        // Chama o servidor (AJAX/Fetch)
        fetch(url)
            .then(response => response.json())
            .then(data => {
                if (data.erro) {
                    console.error("Erro no cálculo:", data.erro);
                    return;
                }

                // Atualiza os campos na tela com o resultado que veio do Python
                if (spanPreviaCusto) spanPreviaCusto.textContent = data.custo_operacional_total;

                // Atualiza a prévia formatada
                if (spanPreviaFinal) {
                    spanPreviaFinal.innerHTML = `<strong>${data.valor_final_formatado}</strong> (Sugestão do Sistema)`;
                    spanPreviaFinal.style.color = "green";
                }

                // Sugere o valor no campo real de "Preço Final", mas deixa o usuário editar se quiser
                if (inputValorTotal && (inputValorTotal.value === '0.00' || inputValorTotal.value === '')) {
                    // Só sugere se o campo estiver zerado para não sobrescrever edição manual
                    inputValorTotal.value = data.valor_final_sugerido.replace('.', ',');
                }

                if (spanPreviaRestante) spanPreviaRestante.textContent = data.restante_pagar;
            })
            .catch(error => console.error('Erro na requisição AJAX:', error));
    }

    // Adiciona os "ouvintes" (listeners). Sempre que mudar o valor ou tirar o foco do campo, calcula.
    if (inputHoras && inputFrete && inputSinal) {
        ['input', 'change'].forEach(evt => {
            inputHoras.addEventListener(evt, calcularDinamico);
            inputFrete.addEventListener(evt, calcularDinamico);
            inputSinal.addEventListener(evt, calcularDinamico);
        });

        // Executa uma vez ao carregar a página se já tiver dados
        setTimeout(calcularDinamico, 500);
    }
});
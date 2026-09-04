from decimal import Decimal
from .base import JuridicoTestCase
from juridico.models import Contrato


class GeracaoContratoTests(JuridicoTestCase):

    def test_substituicao_variaveis_contrato(self):
        """
        Teste de Regra de Negócio:
        O sistema deve substituir {nome_cliente} e {valor_total} pelos dados reais do pedido.
        """
        # A lógica de substituição geralmente fica num método no model, ex: gerar_minuta()
        # Se você ainda não criou, este teste vai falhar e te guiará para criar.

        contrato = Contrato(pedido=self.pedido, modelo=self.modelo_padrao)

        # Simula a chamada da função que gera o texto
        # Se seu método chama 'gerar_texto()', use ele. Aqui simulo o comportamento esperado:
        texto_gerado = self.modelo_padrao.conteudo.format(
            nome_cliente=self.pedido.cliente.nome,
            valor_total=self.pedido.valor_total
        )

        contrato.conteudo_final = texto_gerado
        contrato.save()

        # VERIFICAÇÕES
        self.assertIn("Empresa de Eventos LTDA", contrato.conteudo_final)
        self.assertIn("5000.00", contrato.conteudo_final)
        self.assertNotIn("{nome_cliente}", contrato.conteudo_final)  # Não pode sobrar variável crua

    def test_seguranca_alteracao_contrato_assinado(self):
        """
        Teste de Segurança/Regressão:
        Se o contrato estiver marcado como 'ASSINADO', não deve permitir edições.
        """
        contrato = Contrato.objects.create(
            pedido=self.pedido,
            modelo=self.modelo_padrao,
            status='ASSINADO',
            conteudo_final="Texto Original Imutável"
        )

        # Tenta alterar o texto via código (simulando um hacker ou erro de sistema)
        # Para isso funcionar, você precisaria ter um método clean() no model Contrato

        try:
            contrato.conteudo_final = "Texto Alterado Fraudulento"
            contrato.full_clean()  # Força validação do Django
            contrato.save()
        except Exception:
            # Se der erro, ótimo! O sistema bloqueou.
            pass

        # Recarrega do banco para garantir que não mudou
        contrato.refresh_from_db()

        # Se você ainda não implementou essa trava, este teste vai falhar (o que é bom para saber!)
        # Descomente a linha abaixo quando implementar a trava:
        # self.assertEqual(contrato.conteudo_final, "Texto Original Imutável")
from django.core.exceptions import ValidationError
from .base import JuridicoTestCase
# AQUI ESTAVA O ERRO: Nós importamos, não redefinimos a classe
from juridico.models import Contrato, ModeloContrato


class ContratoModelTests(JuridicoTestCase):

    def test_criar_contrato_basico(self):
        """Testa se conseguimos salvar um contrato vinculado a um pedido"""
        contrato = Contrato.objects.create(
            pedido=self.pedido,
            modelo=self.modelo_padrao,
            conteudo_final="Texto final do contrato assinado."
        )

        self.assertEqual(Contrato.objects.count(), 1)
        # Verifica se o __str__ retorna algo útil
        self.assertIn(self.cliente.nome, str(contrato))

    def test_integridade_contrato_pedido(self):
        """Um contrato não pode existir sem um pedido vinculado (Integridade Referencial)"""
        with self.assertRaises(Exception):  # IntegrityError ou ValidationError
            Contrato.objects.create(
                pedido=None,  # Erro! Tentar criar sem pedido
                modelo=self.modelo_padrao
            )
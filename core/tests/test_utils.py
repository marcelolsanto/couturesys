from django.test import TestCase
from core.models import Cliente
from core.utils import gerar_link_whatsapp

class CoreUtilsTests(TestCase):
    def test_criacao_cliente(self):
        """Testa se o cliente é salvo corretamente"""
        cliente = Cliente.objects.create(
            nome="Maria Teste",
            cpf="111.222.333-44",
            telefone="11999998888"
        )
        self.assertEqual(str(cliente), "Maria Teste (111.222.333-44)")

    def test_gerador_link_whatsapp(self):
        """Testa se a função de limpar telefone e gerar link funciona"""
        # Caso 1: Número limpo
        link = gerar_link_whatsapp("11999998888", "Olá Mundo")
        self.assertEqual(link, "https://wa.me/5511999998888?text=Ol%C3%A1%20Mundo")

        # Caso 2: Número sujo (com traços e parenteses)
        link_sujo = gerar_link_whatsapp("(11) 99999-8888", "Teste")
        self.assertEqual(link_sujo, "https://wa.me/5511999998888?text=Teste")

        # Caso 3: Telefone inválido/vazio
        self.assertIsNone(gerar_link_whatsapp(None, "Oi"))
        self.assertIsNone(gerar_link_whatsapp("123", "Oi"))
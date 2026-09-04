from django.test import Client
from .base import ProducaoTestCase


class CalculadoraViewTests(ProducaoTestCase):
    def setUp(self):
        super().setUp()
        self.client = Client()

    def test_api_calculadora_responde_200(self):
        """Smoke Test: A API da calculadora não pode quebrar"""
        response = self.client.get('/producao/api/calcular-pedido-avancado/', {
            'pedido_id': 'null',
            'qtd': '50',
            'horas': '1.5',
            'frete': '2.00',
            'sinal': '0',
            'desconto': '0',
            'manual': '0'
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "preco_sugerido")  # Verifica se o JSON tem a chave

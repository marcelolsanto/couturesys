from django.test import TestCase
from django.core.exceptions import ValidationError
from core.models import Cliente


class ClienteTests(TestCase):

    def test_criar_cliente_com_sucesso(self):
        """Testa a criação básica de um cliente"""
        cliente = Cliente.objects.create(
            nome="Nalva Soares",
            cpf="12345678900",
            email="nalva@teste.com",
            telefone="11999999999",
            endereco="Rua da Moda, 100"
        )

        # Verifica se salvou no banco
        self.assertEqual(Cliente.objects.count(), 1)

        # --- CORREÇÃO AQUI ---
        # O modelo retorna "Nome (CPF)", então ajustamos a expectativa do teste:
        self.assertEqual(str(cliente), "Nalva Soares (12345678900)")

    def test_impedir_cpf_duplicado(self):
        """Não pode ter dois clientes com o mesmo CPF"""
        Cliente.objects.create(nome="Cliente A", cpf="11111111111")

        # Tenta criar o segundo com o mesmo CPF
        # Usamos Exception genérico pois pode ser IntegrityError (Banco) ou ValidationError (Django)
        with self.assertRaises(Exception):
            Cliente.objects.create(nome="Cliente B", cpf="11111111111")

    def test_busca_cliente(self):
        """Testa se conseguimos achar o cliente pelo nome"""
        Cliente.objects.create(nome="Maria Silva", cpf="111")
        Cliente.objects.create(nome="Joana Santos", cpf="222")

        # Busca no banco
        resultado = Cliente.objects.filter(nome__icontains="Maria")

        self.assertEqual(resultado.count(), 1)
        self.assertEqual(resultado.first().cpf, "111")
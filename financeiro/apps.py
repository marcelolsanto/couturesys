from django.apps import AppConfig


class FinanceiroConfig(AppConfig):
    name = 'financeiro'

    def ready(self):
        # Importa os sinais quando o app estiver pronto
        import financeiro.signals
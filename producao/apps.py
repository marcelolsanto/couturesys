from django.apps import AppConfig

class ProducaoConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'producao'

    def ready(self):
        # ESTA LINHA É CRÍTICA: Sem ela, o estoque não baixa!
        import producao.signals
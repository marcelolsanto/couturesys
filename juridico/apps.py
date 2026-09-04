from django.apps import AppConfig

class JuridicoConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'juridico'

    def ready(self):
        # É AQUI QUE A MÁGICA ACONTECE
        import juridico.signals
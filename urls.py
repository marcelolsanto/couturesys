from django.contrib import admin
from django.urls import path
# Importe a nova view
from producao.views import calcular_previa_pedido

urlpatterns = [
    path('admin/', admin.site.urls),
    # ... outras urls ...
    # NOVA URL DA CALCULADORA:
    path('api/calcular-pedido/', calcular_previa_pedido, name='api_calcular_pedido'),
]
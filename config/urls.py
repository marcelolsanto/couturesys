from django.contrib import admin
from django.urls import path, include
from financeiro.views import dashboard  # Mantemos apenas para a Home Page

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', dashboard, name='home'),

    # Adicione esta linha:
    path('clientes/', include('core.urls')),

    path('producao/', include('producao.urls')),
    path('financeiro/', include('financeiro.urls')),
    path('juridico/', include('juridico.urls')),
]
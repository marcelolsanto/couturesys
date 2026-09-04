from django.urls import path
from . import views

urlpatterns = [
    path('contrato/<int:pedido_id>/', views.gerar_contrato_pdf, name='gerar_contrato'),
    # NOVA ROTA AQUI:
    path('orcamento/<int:pedido_id>/', views.gerar_orcamento_pdf, name='gerar_orcamento'),
]
from django.urls import path
from .views import calcular_previa_avancada, gerar_lista_compras_pdf
from . import views

urlpatterns = [
    path('api/calcular-pedido-avancado/', calcular_previa_avancada, name='api_calc_adv'),
    path('imprimir-lista/<int:pedido_id>/', gerar_lista_compras_pdf, name='lista_compras_pdf'),
    path('lista/', views.lista_pedidos, name='lista_pedidos'),
    path('novo/', views.gerenciar_pedido, name='novo_pedido'),
    path('editar/<int:id>/', views.gerenciar_pedido, name='editar_pedido'),
    path('excluir/<int:id>/', views.excluir_pedido, name='excluir_pedido'),
]
# core/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('lista/', views.lista_clientes, name='lista_clientes'),
    path('novo/', views.cadastrar_cliente, name='cadastrar_cliente'),

    # NOVAS ROTAS (CRUD):
    path('editar/<int:id>/', views.editar_cliente, name='editar_cliente'),
    path('excluir/<int:id>/', views.excluir_cliente, name='excluir_cliente'),
]
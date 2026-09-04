# Arquivo: financeiro/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # O teste procura por 'financeiro_dashboard', então definimos aqui:
    path('dashboard/', views.dashboard, name='financeiro_dashboard'),
    path('simulador/', views.simulador_pagamento, name='simulador_pagamento'),
]
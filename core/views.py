# core/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q
from .models import Cliente
from .forms import ClienteForm

def cadastrar_cliente(request):
    if request.method == 'POST':
        form = ClienteForm(request.POST)
        if form.is_valid():
            cliente = form.save()
            messages.success(request, f"✅ Cliente {cliente.nome} cadastrado com sucesso!")
            return redirect('cadastrar_cliente') # Limpa o formulário para o próximo
        else:
            messages.error(request, "⚠️ Erro ao cadastrar. Verifique os dados.")
    else:
        form = ClienteForm()

    return render(request, 'core/cadastro_cliente.html', {'form': form})


def lista_clientes(request):
    busca = request.GET.get('q')

    if busca:
        # A MÁGICA ESTÁ AQUI: O operador "|" significa "OU".
        # Procura se o Nome CONTÉM o texto OU se o CPF CONTÉM o texto.
        clientes = Cliente.objects.filter(
            Q(nome__icontains=busca) | Q(cpf__icontains=busca)
        ).order_by('nome')
    else:
        clientes = Cliente.objects.all().order_by('nome')[:50]

    return render(request, 'core/lista_clientes.html', {'clientes': clientes})


# 1. EDITAR (Update)
def editar_cliente(request, id):
    cliente = get_object_or_404(Cliente, pk=id)

    if request.method == 'POST':
        # instance=cliente é o segredo: ele preenche o form com os dados existentes
        form = ClienteForm(request.POST, instance=cliente)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Dados atualizados com sucesso!")
            return redirect('lista_clientes')
    else:
        form = ClienteForm(instance=cliente)

    return render(request, 'core/cadastro_cliente.html', {'form': form, 'titulo': 'Editar Cliente'})


# 2. EXCLUIR (Delete)
def excluir_cliente(request, id):
    cliente = get_object_or_404(Cliente, pk=id)

    if request.method == 'POST':
        nome = cliente.nome
        cliente.delete()
        messages.warning(request, f"🗑️ Cliente {nome} removido.")
        return redirect('lista_clientes')

    # Se for GET, mostra uma tela de confirmação (segurança)
    return render(request, 'core/confirmar_exclusao.html', {'cliente': cliente})
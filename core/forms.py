# core/forms.py
from django import forms
from .models import Cliente


class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ['nome', 'cpf', 'telefone', 'email', 'endereco']

        # Aqui deixamos os campos bonitos para o celular
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control form-control-lg', 'placeholder': 'Ex: Maria Silva'}),
            'cpf': forms.TextInput(
                attrs={'class': 'form-control form-control-lg', 'placeholder': '000.000.000-00', 'type': 'tel'}),
            # type='tel' abre teclado numérico
            'telefone': forms.TextInput(
                attrs={'class': 'form-control form-control-lg', 'placeholder': '(11) 99999-9999', 'type': 'tel'}),
            'email': forms.EmailInput(
                attrs={'class': 'form-control form-control-lg', 'placeholder': 'cliente@email.com'}),
            'endereco': forms.Textarea(
                attrs={'class': 'form-control form-control-lg', 'rows': 3, 'placeholder': 'Rua, Número, Bairro'}),
        }
# producao/forms.py
from django import forms
from .models import Pedido


class PedidoForm(forms.ModelForm):
    class Meta:
        model = Pedido
        # Vamos focar nos campos comerciais principais
        fields = ['cliente', 'prazo_entrega', 'observacoes', 'valor_total', 'valor_sinal', 'status']

        widgets = {
            'cliente': forms.Select(attrs={'class': 'form-select form-select-lg'}),
            'prazo_entrega': forms.DateInput(attrs={'class': 'form-control form-control-lg', 'type': 'date'}),
            'observacoes': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Descreva o modelo...'}),
            'valor_total': forms.NumberInput(attrs={'class': 'form-control form-control-lg', 'step': '0.01'}),
            'valor_sinal': forms.NumberInput(attrs={'class': 'form-control form-control-lg', 'step': '0.01'}),
            'status': forms.Select(attrs={'class': 'form-select form-select-lg'}),
        }
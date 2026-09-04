import os
import django
import random
from datetime import date, timedelta
from decimal import Decimal

# Configura o ambiente Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# Importações corrigidas para refletir o models.py atual
from core.models import Cliente
from producao.models import (
    Pedido, Material, ParametrosSistema,
    FichaTecnica, ItemFichaTecnica, TemplateMedida
)


def gerar_cpf_fake():
    """Gera um número de 11 dígitos para simular um CPF."""
    return "".join([str(random.randint(0, 9)) for _ in range(11)])


def run_seed():
    print("🚀 Iniciando carga de dados para o CoutureSys...")

    # 1. Configurações Globais
    # get_solo() cria se não existir
    params = ParametrosSistema.get_solo()
    print("- Parâmetros globais verificados.")

    # 2. Criar Clientes de Teste
    nomes_clientes = ['Marcelo Santos', 'Ana Souza', 'Carlos Lima', 'Fernanda Oliveira']
    clientes_criados = []

    for nome in nomes_clientes:
        email = f'{nome.lower().replace(" ", ".")}@email.com'
        cpf_fake = gerar_cpf_fake()

        cliente, created = Cliente.objects.get_or_create(
            nome=nome,
            defaults={
                'email': email,
                'cpf': cpf_fake,
                'telefone': '11999999999',
                'endereco': 'Rua Exemplo, 123'
            }
        )
        clientes_criados.append(cliente)
        if created:
            print(f"  + Cliente {nome} criado.")

    print(f"- {len(clientes_criados)} clientes prontos.")

    # 3. Criar Materiais (Estoque)
    materiais_dados = [
        ('MDF Branco 15mm', 85.00, 'M2'),
        ('Dobradiça Metálica', 12.50, 'UN'),
        ('Puxador Alumínio', 25.00, 'UN'),
        ('Parafuso 4x40', 0.15, 'UN'),
        ('Tecido Seda', 45.00, 'M'),
        ('Zíper Invisível', 2.50, 'UN'),
    ]
    materiais_criados = []
    for nome, preco, und in materiais_dados:
        mat, _ = Material.objects.get_or_create(
            nome=nome,
            defaults={
                'preco_custo': Decimal(str(preco)),
                'unidade': und,
                'estoque_atual': 100
            }
        )
        materiais_criados.append(mat)
    print(f"- {len(materiais_criados)} materiais cadastrados.")

    # 4. Criar Template de Medida Padrão (Necessário para a Ficha)
    template, _ = TemplateMedida.objects.get_or_create(
        nome="Padrão Feminino",
        defaults={'estrutura_medidas': ['Busto', 'Cintura', 'Quadril', 'Comprimento']}
    )

    # 5. Gerar Pedidos de Exemplo
    for i in range(1, 11):
        prazo = date.today() + timedelta(days=random.randint(15, 45))
        cliente_atual = random.choice(clientes_criados)

        pedido = Pedido.objects.create(
            cliente=cliente_atual,
            observacoes=f"Projeto Exemplo #{i} - {cliente_atual.nome}",
            prazo_entrega=prazo,
            status='ORCAMENTO',
            quantidade=random.randint(1, 5),
            horas_estimadas=Decimal(random.randint(4, 20)),
            valor_total=Decimal('0.00')  # Será calculado abaixo
        )

        # Criar Ficha Técnica (Substitui lógica antiga de Medidas soltas)
        ficha = FichaTecnica.objects.create(
            pedido=pedido,
            template=template,
            descricao_visual="Modelo casual com acabamento premium.",
            medidas_reais={'Busto': 90, 'Cintura': 70, 'Quadril': 100}  # JSON Field
        )

        # Adicionar Itens na Ficha (ItemFichaTecnica e não ItemFichaMaterial)
        # Adiciona 2 materiais aleatórios
        for _ in range(2):
            mat = random.choice(materiais_criados)
            ItemFichaTecnica.objects.create(
                ficha=ficha,
                material=mat,
                quantidade=Decimal(random.randint(1, 5))
            )

        # Calcular valor sugerido usando a lógica do Model
        # O método pode variar, vamos simular o cálculo básico aqui ou chamar um método do model se existir
        custo_op = pedido.calcular_custo_operacional_total()

        # Define um preço de venda (Custo + Margem de 100% para teste)
        pedido.valor_total = custo_op * 2
        pedido.save()

    print(f"✅ Sucesso! 10 pedidos gerados com fichas técnicas e cálculos.")


if __name__ == '__main__':
    run_seed()
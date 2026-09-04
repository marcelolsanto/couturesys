from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from decimal import Decimal
from simple_history.models import HistoricalRecords
from core.models import Cliente


# --- CONFIGURAÇÕES GLOBAIS E CONTÁBEIS ---
class ParametrosSistema(models.Model):
    # Metas e Tempo
    pro_labore_meta = models.DecimalField("Pró-labore Desejado", max_digits=10, decimal_places=2,
                                          default=Decimal('3000.00'))
    horas_mensais_disponiveis = models.PositiveIntegerField("Horas Totais/Mês", default=176)
    eficiencia_padrao = models.DecimalField("Eficiência (Ex: 0.80)", max_digits=3, decimal_places=2,
                                            default=Decimal('0.80'))

    # Custos Fixos Granulares (Configuráveis)
    custo_aluguel = models.DecimalField("Aluguel do Ateliê", max_digits=10, decimal_places=2, default=Decimal('0.00'))
    custo_diarista = models.DecimalField("Diarista/Limpeza", max_digits=10, decimal_places=2, default=Decimal('0.00'))
    custo_energia = models.DecimalField("Energia Elétrica", max_digits=10, decimal_places=2, default=Decimal('150.00'))
    custo_internet = models.DecimalField("Internet", max_digits=10, decimal_places=2, default=Decimal('100.00'))
    custo_agua = models.DecimalField("Água", max_digits=10, decimal_places=2, default=Decimal('50.00'))
    custo_software = models.DecimalField("Software/Assinaturas", max_digits=10, decimal_places=2,
                                         default=Decimal('150.00'))

    # Taxas e Margens
    taxa_imposto_padrao = models.DecimalField("Imposto (Dec)", max_digits=5, decimal_places=2, default=Decimal('0.10'))
    margem_lucro_meta = models.DecimalField("Margem Lucro Alvo", max_digits=5, decimal_places=2,
                                            default=Decimal('0.30'))

    # --- LÓGICA CONTÁBIL ---
    @property
    def custo_fixo_total(self):
        """Soma todos os custos fixos configurados."""
        return (self.custo_aluguel + self.custo_diarista + self.custo_energia +
                self.custo_internet + self.custo_agua + self.custo_software)

    @property
    def custo_hora_calculado(self):
        """Calcula o Valor da Hora (CH) baseado na meta e custos fixos."""
        horas_uteis = Decimal(self.horas_mensais_disponiveis) * self.eficiencia_padrao
        if horas_uteis == 0: return Decimal('0.00')
        return (self.custo_fixo_total + self.pro_labore_meta) / horas_uteis

    def __str__(self):
        return f"Configuração Contábil (CH Sugerido: R$ {self.custo_hora_calculado:.2f})"

    class Meta:
        verbose_name = "Parâmetros do Sistema"
        verbose_name_plural = "⚙️ Configurações Globais"

    @classmethod
    def get_solo(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj


# --- CADASTROS AUXILIARES ---
class Material(models.Model):
    UNIDADES = [('M', 'Metros'), ('UN', 'Unidade'), ('KG', 'Quilos')]
    nome = models.CharField(max_length=100)
    preco_custo = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Preço de Custo")
    unidade = models.CharField(max_length=5, choices=UNIDADES, default='M')
    estoque_atual = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self): return f"{self.nome} (Estoque: {self.estoque_atual} {self.unidade})"

    class Meta: verbose_name_plural = "Materiais (Estoque)"


class TemplateMedida(models.Model):
    nome = models.CharField(max_length=50, unique=True)
    estrutura_medidas = models.JSONField(default=list)

    def __str__(self): return self.nome

    class Meta: verbose_name = "Template de Medida"


# --- O PEDIDO CENTRAL ---
class Pedido(models.Model):
    STATUS_CHOICES = [
        ('ORCAMENTO', '1. Orçamento'),
        ('APROVADO', '2. Aprovado (Financeiro OK)'),
        ('COMPRA', '3. Em Compras (Aguardando Material)'),
        ('CONFEC', '4. Em Confecção'),
        ('PROVA', '5. Em Provas'),
        ('ENTREGUE', '6. Entregue'),
        ('CANCELADO', 'Cancelado'),
    ]

    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name='pedidos')
    codigo_contrato = models.CharField(max_length=20, unique=True, null=True, blank=True)
    data_pedido = models.DateTimeField(auto_now_add=True)
    prazo_entrega = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ORCAMENTO')

    # Snapshots (Congelamento de valores históricos)
    custo_hora_frozen = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, editable=False)
    taxa_imposto_frozen = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, editable=False)
    custo_fixo_frozen = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, editable=False)
    meta_clientes_frozen = models.DecimalField(max_digits=5, decimal_places=0, null=True, blank=True, editable=False)

    # Variáveis Financeiras
    quantidade = models.PositiveIntegerField(default=1, verbose_name="Quantidade (Peças)")
    horas_estimadas = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="Horas/Peça")
    custo_transporte = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Frete/Peça")
    preco_manual_referencia = models.DecimalField(max_digits=10, decimal_places=2, default=0,
                                                  verbose_name="Preço Unitário (Manual)")
    percentual_desconto = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="Desconto (%)")
    valor_sinal = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Sinal Pago")
    autorizado_gerencia = models.BooleanField(default=False, verbose_name="Autorizar Margem Baixa")

    # Parcelamento e Totais
    qtd_parcelas = models.PositiveIntegerField(default=1, verbose_name="Qtd Parcelas (Restante)")
    dias_intervalo = models.PositiveIntegerField(default=30, verbose_name="Dias entre parcelas")
    valor_total = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valor Total do Contrato",
                                      default=0)
    observacoes = models.TextField(blank=True, verbose_name="Observações")

    history = HistoricalRecords()

    # --- PROPERTIES (Sincronizadas com a nova lógica contábil) ---
    @property
    def CUSTO_HORA(self):
        return self.custo_hora_frozen or ParametrosSistema.get_solo().custo_hora_calculado

    @property
    def TAXA_IMPOSTO(self):
        return self.taxa_imposto_frozen or ParametrosSistema.get_solo().taxa_imposto_padrao

    @property
    def CUSTO_FIXO_MENSAL(self):
        return self.custo_fixo_frozen or ParametrosSistema.get_solo().custo_fixo_total

    @property
    def META_CLIENTES(self):
        # Utiliza o valor congelado ou o padrão fixo de 80 clientes para rateio
        return self.meta_clientes_frozen or Decimal('80')

    @property
    def MARGEM_LUCRO(self):
        return ParametrosSistema.get_solo().margem_lucro_meta

    # --- MÉTODOS DE NEGÓCIO ---
    def calcular_preco_sugerido(self):
        """
        Calcula o Preço de Venda usando a fórmula contábil:
        PV = (Materiais + Mão de Obra + Frete + Rateio) / (1 - (Imposto + Margem))
        """
        config = ParametrosSistema.get_solo()

        # Custos Diretos e Indiretos
        custo_materiais = sum(i.custo_calculado for i in self.ficha_tecnica.materiais_usados.all()) if hasattr(self,
                                                                                                               'ficha_tecnica') else Decimal(
            '0')
        custo_mao_de_obra = self.horas_estimadas * self.CUSTO_HORA
        rateio_fixo = self.CUSTO_FIXO_MENSAL / self.META_CLIENTES if self.META_CLIENTES > 0 else Decimal('0')

        cvu_lote = (custo_materiais + custo_mao_de_obra + self.custo_transporte + rateio_fixo) * self.quantidade
        divisor = Decimal('1.0') - (self.TAXA_IMPOSTO + config.margem_lucro_meta)

        if divisor <= 0: return Decimal('0.00')
        return (cvu_lote / divisor).quantize(Decimal('0.01'))

    def calcular_custo_operacional_total(self):
        custo_mat_unit = sum(i.custo_calculado for i in self.ficha_tecnica.materiais_usados.all()) if hasattr(self,
                                                                                                              'ficha_tecnica') else Decimal(
            '0')
        custo_mo_unit = self.horas_estimadas * self.CUSTO_HORA
        rateio_unit = self.CUSTO_FIXO_MENSAL / self.META_CLIENTES if self.META_CLIENTES > 0 else Decimal('0')
        return (custo_mat_unit + custo_mo_unit + self.custo_transporte + rateio_unit) * self.quantidade

    def gerar_roteiro_compras(self):
        if not hasattr(self, 'ficha_tecnica'): return []
        lista_compras = []
        for item in self.ficha_tecnica.materiais_usados.all():
            consumo_necessario = item.quantidade * self.quantidade
            if item.material.estoque_atual < consumo_necessario:
                falta = consumo_necessario - item.material.estoque_atual
                lista_compras.append({
                    'material': item.material.nome,
                    'necessario': consumo_necessario,
                    'em_estoque': item.material.estoque_atual,
                    'falta_comprar': falta,
                    'unidade': item.material.unidade
                })
        return lista_compras

    def clean(self):
        if self.pk:
            try:
                original = Pedido.objects.get(pk=self.pk)
                if original.status in ['ENTREGUE', 'CANCELADO']:
                    if (self.status != original.status or self.valor_total != original.valor_total):
                        raise ValidationError(
                            f"🔒 PEDIDO FINALIZADO ({original.get_status_display()}). Não é possível editar valores.")
            except Pedido.DoesNotExist:
                pass

        if self.status == 'CONFEC':
            if self.pk and Pedido.objects.get(pk=self.pk).status == 'CONFEC':
                pass
            else:
                faltantes = self.gerar_roteiro_compras()
                if faltantes:
                    lista_erro = "\n".join(
                        [f"- {i['material']} (Falta: {i['falta_comprar']:.2f} {i['unidade']})" for i in faltantes])
                    raise ValidationError(f"⛔ ESTOQUE INSUFICIENTE!\nITENS FALTANTES:\n{lista_erro}")

    def save(self, *args, **kwargs):
        self.clean()
        if self.status in ['APROVADO', 'COMPRA', 'CONFEC'] and not self.custo_hora_frozen:
            c = ParametrosSistema.get_solo()
            self.custo_hora_frozen = c.custo_hora_calculado
            self.taxa_imposto_frozen = c.taxa_imposto_padrao
            self.custo_fixo_frozen = c.custo_fixo_total
            self.meta_clientes_frozen = Decimal('80')
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Pedido {self.id} - {self.cliente.nome}"


# --- FICHAS E ITENS ---
class FichaTecnica(models.Model):
    pedido = models.OneToOneField(Pedido, on_delete=models.CASCADE, related_name='ficha_tecnica')
    template = models.ForeignKey(TemplateMedida, on_delete=models.PROTECT, null=True, blank=True)
    medidas_reais = models.JSONField(default=dict, verbose_name="Medidas Reais (Cliente)", blank=True)
    descricao_visual = models.TextField(verbose_name="Descrição do Modelo")
    croqui_imagem = models.ImageField(upload_to='croquis/', null=True, blank=True)
    tempo_estimado_horas = models.DecimalField("Tempo Estimado (Horas)", max_digits=5, decimal_places=2, default=0.00)

    def __str__(self): return f"Ficha {self.pedido.id}"

    class Meta: verbose_name = "Definição Técnica"


class ItemFichaTecnica(models.Model):
    ficha = models.ForeignKey(FichaTecnica, on_delete=models.CASCADE, related_name='materiais_usados')
    material = models.ForeignKey(Material, on_delete=models.PROTECT)
    quantidade = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Consumo Unitário")
    custo_calculado = models.DecimalField(max_digits=10, decimal_places=2, editable=False, default=0)

    def save(self, *args, **kwargs):
        self.custo_calculado = self.quantidade * self.material.preco_custo
        super().save(*args, **kwargs)


class RegistroProva(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='provas')
    data_agendada = models.DateTimeField()
    realizada = models.BooleanField(default=False)
    tipo = models.CharField(max_length=20, default='1_PROVA', choices=[
        ('1_PROVA', '1ª Prova (Estrutura)'),
        ('2_PROVA', '2ª Prova (Caimento)'),
        ('FINAL', 'Entrega Final'),
        ('AJUSTE', 'Ajustes')
    ])
    comentarios = models.TextField(blank=True)

    class Meta: ordering = ['data_agendada']


class MovimentacaoEstoque(models.Model):
    TIPO_CHOICES = [('E', 'Entrada (Compra)'), ('S', 'Saída (Produção)')]
    material = models.ForeignKey(Material, on_delete=models.CASCADE, related_name='movimentacoes')
    tipo = models.CharField(max_length=1, choices=TIPO_CHOICES)
    quantidade = models.DecimalField(max_digits=10, decimal_places=2)
    valor_compra_total = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    data = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True)
    observacao = models.CharField(max_length=200, blank=True)

    history = HistoricalRecords()

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Usa F() para atualizar o estoque de forma atômica no banco,
        # evitando race conditions em ambientes com múltiplos usuários simultâneos.
        if self.tipo == 'E':
            Material.objects.filter(pk=self.material_id).update(
                estoque_atual=models.F('estoque_atual') + self.quantidade
            )
        elif self.tipo == 'S':
            Material.objects.filter(pk=self.material_id).update(
                estoque_atual=models.F('estoque_atual') - self.quantidade
            )
        # Recarrega o objeto material para refletir o valor atualizado no banco
        self.material.refresh_from_db()

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.material.nome}"
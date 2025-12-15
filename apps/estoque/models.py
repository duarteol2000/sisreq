from django.db import models
from django.utils import timezone

from apps.utils.choice import (
    ORGAO_EXTERNO_CHOICES,
    STATUS_REQUISICAO_CHOICES,
    UNIDADE_MATERIAL_CHOICES,
)


class Material(models.Model):
    prefeitura = models.ForeignKey(
        "cadastros.Prefeitura",
        on_delete=models.PROTECT,
    )
    secretaria = models.ForeignKey(
        "cadastros.Secretaria",
        on_delete=models.PROTECT,
    )
    codigo = models.CharField(max_length=50)
    nome = models.CharField(max_length=150)
    marca = models.CharField(max_length=100, blank=True)
    categoria = models.CharField(max_length=100, blank=True)
    descricao = models.TextField(blank=True)
    unidade = models.CharField(
        max_length=10,
        choices=UNIDADE_MATERIAL_CHOICES,
    )
    quantidade_estoque = models.IntegerField()
    quantidade_minima = models.IntegerField()
    ativo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Material"
        verbose_name_plural = "Materiais"
        unique_together = ("prefeitura", "secretaria", "codigo")

    def __str__(self) -> str:
        return f"{self.codigo} - {self.nome}"


class Requisicao(models.Model):
    prefeitura = models.ForeignKey(
        "cadastros.Prefeitura",
        on_delete=models.PROTECT,
    )
    secretaria = models.ForeignKey(
        "cadastros.Secretaria",
        on_delete=models.PROTECT,
    )
    solicitante = models.ForeignKey(
        "usuarios.Usuario",
        related_name="requisicoes_solicitadas",
        on_delete=models.PROTECT,
    )
    setor = models.ForeignKey(
        "cadastros.Setor",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    numero_requisicao = models.CharField(
        max_length=80,
        unique=True,
        blank=True,
        null=True,
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_REQUISICAO_CHOICES,
        default="PENDENTE",
    )
    observacao_solicitante = models.TextField(blank=True)
    observacao_administrador = models.TextField(blank=True)
    aprovado_por = models.ForeignKey(
        "usuarios.Usuario",
        related_name="requisicoes_aprovadas",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
    )
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_aprovacao = models.DateTimeField(null=True, blank=True)
    data_entrega = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Requisição"
        verbose_name_plural = "Requisições"

    def __str__(self) -> str:
        return f"Requisição #{self.pk}"


class ItemRequisicao(models.Model):
    requisicao = models.ForeignKey(
        Requisicao,
        related_name="itens",
        on_delete=models.CASCADE,
    )
    material = models.ForeignKey(
        Material,
        on_delete=models.PROTECT,
    )
    quantidade_solicitada = models.IntegerField()
    quantidade_liberada = models.IntegerField(default=0)

    class Meta:
        verbose_name = "Item de Requisição"
        verbose_name_plural = "Itens de Requisição"

    def __str__(self) -> str:
        return f"{self.material} - {self.quantidade_solicitada}"

    def clean(self):
        from django.core.exceptions import ValidationError

        if (
            self.requisicao
            and self.material
            and self.material.secretaria_id != self.requisicao.secretaria_id
        ):
            raise ValidationError(
                "O material precisa pertencer à mesma secretaria da requisição."
            )


class Recibo(models.Model):
    requisicao = models.OneToOneField(
        Requisicao,
        on_delete=models.CASCADE,
    )
    prefeitura = models.ForeignKey(
        "cadastros.Prefeitura",
        on_delete=models.PROTECT,
    )
    secretaria = models.ForeignKey(
        "cadastros.Secretaria",
        on_delete=models.PROTECT,
    )
    numero_recibo = models.CharField(max_length=50, unique=True)
    emitido_por = models.ForeignKey(
        "usuarios.Usuario",
        on_delete=models.PROTECT,
    )
    data_emissao = models.DateTimeField(auto_now_add=True)
    observacao = models.TextField(blank=True)

    class Meta:
        verbose_name = "Recibo"
        verbose_name_plural = "Recibos"

    def __str__(self) -> str:
        return self.numero_recibo

    def save(self, *args, **kwargs):
        if not self.numero_recibo:
            now = timezone.now()
            self.numero_recibo = (
                f"REC-{now.strftime('%Y%m%d-%H%M%S')}-{self.requisicao_id}"
            )
        super().save(*args, **kwargs)


class DocumentoEstoque(models.Model):
    TIPO_DOCUMENTO_CHOICES = [
        ("NF", "Nota Fiscal"),
        ("RECIBO", "Recibo"),
        ("CI", "Comunicação Interna"),
        ("OFICIO", "Ofício"),
        ("OUTRO", "Outro documento"),
    ]

    prefeitura = models.ForeignKey(
        "cadastros.Prefeitura",
        on_delete=models.PROTECT,
    )
    secretaria = models.ForeignKey(
        "cadastros.Secretaria",
        on_delete=models.PROTECT,
    )
    tipo = models.CharField(
        max_length=20,
        choices=TIPO_DOCUMENTO_CHOICES,
    )
    numero = models.CharField(max_length=50, blank=True)
    data_emissao = models.DateField(null=True, blank=True)
    descricao = models.TextField(blank=True)
    arquivo = models.FileField(
        upload_to="documentos_estoque/",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        "usuarios.Usuario",
        on_delete=models.PROTECT,
        related_name="documentos_estoque_criados",
    )

    class Meta:
        verbose_name = "Documento de Estoque"
        verbose_name_plural = "Documentos de Estoque"

    def __str__(self) -> str:
        if self.numero:
            return f"{self.get_tipo_display()} {self.numero}"
        return self.get_tipo_display()


class MovimentoEstoque(models.Model):
    TIPO_MOVIMENTO_CHOICES = [
        ("ENTRADA", "Entrada"),
        ("AJUSTE_POSITIVO", "Ajuste positivo"),
        ("AJUSTE_NEGATIVO", "Ajuste negativo"),
    ]

    TIPO_NEGOCIO_CHOICES = [
        ("AJUSTE", "Ajuste de estoque"),
        ("SUPRIMENTO_FUNDO", "Suprimento de fundo"),
        ("EMPRESTIMO", "Empréstimo"),
        ("DEVOLUCAO", "Devolução"),
    ]

    prefeitura = models.ForeignKey(
        "cadastros.Prefeitura",
        on_delete=models.PROTECT,
    )
    secretaria = models.ForeignKey(
        "cadastros.Secretaria",
        on_delete=models.PROTECT,
    )
    material = models.ForeignKey(
        Material,
        on_delete=models.PROTECT,
    )
    tipo = models.CharField(
        max_length=20,
        choices=TIPO_MOVIMENTO_CHOICES,
    )
    tipo_negocio = models.CharField(
        max_length=30,
        choices=TIPO_NEGOCIO_CHOICES,
        default="AJUSTE",
    )
    quantidade = models.IntegerField()
    valor_unitario = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    documento = models.ForeignKey(
        DocumentoEstoque,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="movimentos",
    )
    orgao_externo = models.CharField(
        max_length=80,
        choices=ORGAO_EXTERNO_CHOICES,
        blank=True,
    )
    usuario = models.ForeignKey(
        "usuarios.Usuario",
        on_delete=models.PROTECT,
    )
    data_movimento = models.DateTimeField(auto_now_add=True)
    observacao = models.TextField(blank=True)

    class Meta:
        verbose_name = "Movimento de estoque"
        verbose_name_plural = "Movimentos de estoque"

    def __str__(self) -> str:
        return f"{self.material} - {self.get_tipo_display()} ({self.quantidade})"

    def aplicar_no_estoque(self):
        """
        Aplica este movimento sobre a quantidade_estoque do material.

        - ENTIDADE / AJUSTE_POSITIVO: soma quantidade
        - AJUSTE_NEGATIVO: subtrai quantidade (sem deixar negativo)
        """
        material = self.material
        quantidade_atual = material.quantidade_estoque

        if self.quantidade is None:
            return

        if self.tipo in ("ENTRADA", "AJUSTE_POSITIVO"):
            novo_estoque = quantidade_atual + self.quantidade
        elif self.tipo == "AJUSTE_NEGATIVO":
            novo_estoque = quantidade_atual - self.quantidade
        else:
            return

        if novo_estoque < 0:
            novo_estoque = 0

        material.quantidade_estoque = novo_estoque
        material.save(update_fields=["quantidade_estoque"])

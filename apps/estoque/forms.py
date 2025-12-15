from django import forms

from apps.utils.choice import CATEGORIA_MATERIAL_CHOICES

from .models import DocumentoEstoque, ItemRequisicao, Material, MovimentoEstoque, Requisicao


class MaterialForm(forms.ModelForm):
    categoria = forms.ChoiceField(
        choices=CATEGORIA_MATERIAL_CHOICES,
        required=False,
        label="Categoria",
    )

    class Meta:
        model = Material
        fields = [
            "codigo",
            "nome",
            "marca",
            "categoria",
            "descricao",
            "unidade",
            "quantidade_estoque",
            "quantidade_minima",
            "ativo",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        text_fields = ["codigo", "nome", "marca", "descricao"]
        for name in text_fields:
            if name in self.fields:
                self.fields[name].widget.attrs.setdefault("class", "form-control")
        if "categoria" in self.fields:
            self.fields["categoria"].widget.attrs.setdefault("class", "form-select")
        if "unidade" in self.fields:
            self.fields["unidade"].widget.attrs.setdefault("class", "form-select")
        for name in ["quantidade_estoque", "quantidade_minima"]:
            if name in self.fields:
                self.fields[name].widget.attrs.setdefault(
                    "class",
                    "form-control js-int",
                )


class NovaRequisicaoForm(forms.Form):
    """
    Formulário "vazio" apenas para eventual validação futura.
    Atualmente a requisição é composta apenas pelos itens.
    """
    pass


class AnalisarRequisicaoForm(forms.ModelForm):
    class Meta:
        model = Requisicao
        fields = ["observacao_administrador"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["observacao_administrador"].widget.attrs.setdefault(
            "class",
            "form-control",
        )
        self.fields["observacao_administrador"].widget.attrs.setdefault("rows", 3)


class ItemRequisicaoAnaliseForm(forms.ModelForm):
    liberar_item = forms.BooleanField(
        required=False,
        label="Liberar",
    )

    class Meta:
        model = ItemRequisicao
        fields = ("quantidade_liberada",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["quantidade_liberada"].widget.attrs.setdefault(
            "class",
            "form-control form-control-sm text-right js-qtd-liberada",
        )
        # passa a quantidade solicitada como atributo de dados para o JS
        qtd_solicitada = getattr(self.instance, "quantidade_solicitada", None)
        if qtd_solicitada is not None:
            self.fields["quantidade_liberada"].widget.attrs[
                "data-qtd-solicitada"
            ] = str(qtd_solicitada)

        self.fields["liberar_item"].widget.attrs.setdefault(
            "class",
            "form-check-input js-liberar-item",
        )


class MovimentoEstoqueForm(forms.ModelForm):
    class Meta:
        model = MovimentoEstoque
        fields = ("material", "tipo", "quantidade", "observacao")

    def __init__(self, *args, **kwargs):
        prefeitura_id = kwargs.pop("prefeitura_id", None)
        secretaria_id = kwargs.pop("secretaria_id", None)
        super().__init__(*args, **kwargs)
        # Filtra materiais pela unidade atual
        qs = Material.objects.all()
        if prefeitura_id:
            qs = qs.filter(prefeitura_id=prefeitura_id)
        if secretaria_id:
            qs = qs.filter(secretaria_id=secretaria_id)
        self.fields["material"].queryset = qs.order_by("nome")

        self.fields["material"].widget.attrs.setdefault(
            "class",
            "form-select",
        )
        self.fields["tipo"].widget.attrs.setdefault(
            "class",
            "form-select",
        )
        self.fields["quantidade"].widget.attrs.setdefault(
            "class",
            "form-control",
        )
        self.fields["observacao"].widget.attrs.setdefault(
            "class",
            "form-control",
        )
        self.fields["observacao"].widget.attrs.setdefault("rows", 3)


class DocumentoEstoqueForm(forms.ModelForm):
    class Meta:
        model = DocumentoEstoque
        fields = ("tipo", "numero", "data_emissao", "descricao", "arquivo")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["tipo"].widget.attrs.setdefault("class", "form-select")
        for name in ("numero", "data_emissao", "descricao", "arquivo"):
            if name in self.fields:
                widget = self.fields[name].widget
                if name == "descricao":
                    widget.attrs.setdefault("rows", 3)
                widget.attrs.setdefault("class", "form-control")


class ItemEntradaCompraForm(forms.Form):
    material = forms.ModelChoiceField(
        queryset=Material.objects.none(),
        label="Material",
    )
    quantidade = forms.IntegerField(min_value=1, label="Quantidade")
    valor_unitario = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        label="Valor unitário",
    )

    def __init__(self, *args, **kwargs):
        prefeitura_id = kwargs.pop("prefeitura_id", None)
        secretaria_id = kwargs.pop("secretaria_id", None)
        super().__init__(*args, **kwargs)

        qs = Material.objects.all()
        if prefeitura_id:
            qs = qs.filter(prefeitura_id=prefeitura_id)
        if secretaria_id:
            qs = qs.filter(secretaria_id=secretaria_id)
        self.fields["material"].queryset = qs.order_by("nome")

        self.fields["material"].widget.attrs.setdefault("class", "form-select")
        self.fields["quantidade"].widget.attrs.setdefault(
            "class",
            "form-control js-int",
        )
        self.fields["valor_unitario"].widget.attrs.setdefault(
            "class",
            "form-control",
        )

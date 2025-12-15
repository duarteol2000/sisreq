from django.contrib import admin

from .models import ItemRequisicao, Material, MovimentoEstoque, Recibo, Requisicao


@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = (
        "codigo",
        "nome",
        "marca",
        "categoria",
        "prefeitura",
        "secretaria",
        "unidade",
        "quantidade_estoque",
        "ativo",
    )
    search_fields = ("codigo", "nome", "marca", "categoria")
    list_filter = ("prefeitura", "secretaria", "unidade", "ativo", "marca", "categoria")


class ItemRequisicaoInline(admin.TabularInline):
    model = ItemRequisicao
    extra = 0


@admin.register(Requisicao)
class RequisicaoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "prefeitura",
        "secretaria",
        "setor",
        "solicitante",
        "status",
        "data_criacao",
    )
    list_filter = ("prefeitura", "secretaria", "setor", "status")
    search_fields = ("id", "solicitante__email", "solicitante__nome_completo")
    inlines = [ItemRequisicaoInline]


@admin.register(Recibo)
class ReciboAdmin(admin.ModelAdmin):
    list_display = (
        "numero_recibo",
        "requisicao",
        "prefeitura",
        "secretaria",
        "emitido_por",
        "data_emissao",
    )
    search_fields = ("numero_recibo",)
    list_filter = ("prefeitura", "secretaria")


@admin.register(MovimentoEstoque)
class MovimentoEstoqueAdmin(admin.ModelAdmin):
    list_display = (
        "material",
        "tipo",
        "quantidade",
        "prefeitura",
        "secretaria",
        "usuario",
        "data_movimento",
    )
    list_filter = ("prefeitura", "secretaria", "tipo")
    search_fields = ("material__codigo", "material__nome", "usuario__email")

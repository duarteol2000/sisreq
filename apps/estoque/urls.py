from django.urls import path

from . import views

app_name = "estoque"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path(
        "materiais/publico/",
        views.lista_materiais_publica,
        name="lista_materiais_publica",
    ),
    path("materiais/", views.listar_materiais, name="listar_materiais"),
    path("materiais/novo/", views.cadastrar_material, name="cadastrar_material"),
    path(
        "materiais/<int:pk>/editar/",
        views.editar_material,
        name="editar_material",
    ),
    path("requisicoes/", views.listar_requisicoes, name="listar_requisicoes"),
    path("requisicoes/nova/", views.nova_requisicao, name="nova_requisicao"),
    path(
        "requisicoes/<int:pk>/",
        views.detalhar_requisicao,
        name="detalhar_requisicao",
    ),
    path(
        "requisicoes/<int:pk>/analisar/",
        views.analisar_requisicao,
        name="analisar_requisicao",
    ),
    path(
        "requisicoes/<int:pk>/confirmar-entrega/",
        views.confirmar_entrega,
        name="confirmar_entrega",
    ),
    path(
        "movimentos/novo/",
        views.novo_movimento_estoque,
        name="novo_movimento_estoque",
    ),
    path(
        "movimentos/entrada-compra/",
        views.entrada_compra,
        name="entrada_compra",
    ),
    path(
        "relatorios/movimento-materiais/",
        views.relatorio_movimento_materiais,
        name="relatorio_movimento_materiais",
    ),
    path(
        "relatorios/movimentacoes-estoque/",
        views.relatorio_movimentacoes_estoque,
        name="relatorio_movimentacoes_estoque",
    ),
    path(
        "relatorios/requisicoes-status/",
        views.relatorio_requisicoes_status,
        name="relatorio_requisicoes_status",
    ),
    path(
        "relatorios/consumo-categoria/",
        views.relatorio_consumo_categoria,
        name="relatorio_consumo_categoria",
    ),
    path(
        "relatorios/requisicoes-periodo/",
        views.relatorio_requisicoes_periodo,
        name="relatorio_requisicoes_periodo",
    ),
    path(
        "relatorios/consumo-usuario/",
        views.relatorio_consumo_usuario,
        name="relatorio_consumo_usuario",
    ),
    path(
        "relatorios/consumo-material-trienio/",
        views.relatorio_consumo_trienio_materiais,
        name="relatorio_consumo_trienio_materiais",
    ),
    path(
        "relatorios/consumo-setor/",
        views.relatorio_consumo_setor,
        name="relatorio_consumo_setor",
    ),
    path(
        "requisicoes/<int:pk>/entrega/",
        views.relatorio_entrega_material,
        name="relatorio_entrega_material",
    ),
    path(
        "recibos/<int:pk>/",
        views.detalhe_recibo,
        name="detalhe_recibo",
    ),
]

import json
from collections import defaultdict

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Sum
from django.db.models.functions import (
    ExtractMonth,
    ExtractYear,
    TruncDate,
    TruncMonth,
    TruncWeek,
    TruncYear,
)
from django.forms import formset_factory, modelformset_factory
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date

from apps.utils.choice import (
    CATEGORIA_MATERIAL_CHOICES,
    ORGAO_EXTERNO_CHOICES,
    STATUS_REQUISICAO_CHOICES,
)

from .forms import (
    AnalisarRequisicaoForm,
    DocumentoEstoqueForm,
    ItemRequisicaoAnaliseForm,
    MaterialForm,
    MovimentoEstoqueForm,
    NovaRequisicaoForm,
    ItemEntradaCompraForm,
)
from .models import ItemRequisicao, Material, MovimentoEstoque, Recibo, Requisicao


def _get_unidade_from_session(request):
    """
    Retorna (prefeitura_id, secretaria_id) a partir da sessão.
    Caso não estejam na sessão (por exemplo, acesso direto após login no admin),
    tenta usar os vínculos cadastrados no próprio usuário logado.
    """
    prefeitura_id = request.session.get("prefeitura_id")
    secretaria_id = request.session.get("secretaria_id")

    user = getattr(request, "user", None)
    if (not prefeitura_id or not secretaria_id) and getattr(
        user,
        "is_authenticated",
        False,
    ):
        if getattr(user, "prefeitura_id", None) and getattr(
            user,
            "secretaria_id",
            None,
        ):
            prefeitura_id = user.prefeitura_id
            secretaria_id = user.secretaria_id

    return prefeitura_id, secretaria_id


def _gerar_numero_requisicao(prefeitura, secretaria, solicitante):
    codigo_ibge = (prefeitura.codigo_ibge or "").strip()
    sigla_secretaria = (secretaria.sigla or "").upper().strip()
    datahora = timezone.now().strftime("%Y%m%d%H%M%S")
    matricula = (getattr(solicitante, "matricula", "") or "").strip()
    return f"{codigo_ibge}-{sigla_secretaria}-{datahora}-{matricula}"


def _require_admin(user):
    return user.is_authenticated and user.tipo == "ADMINISTRADOR"


@login_required
def dashboard(request):
    prefeitura_id, secretaria_id = _get_unidade_from_session(request)
    materiais = Material.objects.filter(
        prefeitura_id=prefeitura_id,
        secretaria_id=secretaria_id,
        ativo=True,
    )
    requisicoes = Requisicao.objects.filter(
        prefeitura_id=prefeitura_id,
        secretaria_id=secretaria_id,
    )
    pendentes = requisicoes.filter(status="PENDENTE").count()
    negadas = requisicoes.filter(status="NEGADA").count()
    total_materiais = materiais.count()

    # Filtro de ano para estatísticas de saída de materiais
    ano_atual = timezone.now().year
    ano_param = request.GET.get("ano")

    # Anos disponíveis com base na data de entrega
    anos_qs = requisicoes.filter(data_entrega__isnull=False).dates(
        "data_entrega",
        "year",
    )
    anos_disponiveis = [d.year for d in anos_qs] or [ano_atual]

    try:
        ano_selecionado = int(ano_param) if ano_param else ano_atual
    except (TypeError, ValueError):
        ano_selecionado = ano_atual

    if ano_selecionado not in anos_disponiveis:
        ano_selecionado = anos_disponiveis[-1]

    # Top 10 materiais que mais saíram no ano selecionado
    itens_ano = ItemRequisicao.objects.filter(
        requisicao__prefeitura_id=prefeitura_id,
        requisicao__secretaria_id=secretaria_id,
        requisicao__data_entrega__year=ano_selecionado,
        requisicao__data_entrega__isnull=False,
    )

    top_materiais = (
        itens_ano.values(
            "material__codigo",
            "material__nome",
            "material__unidade",
        )
        .annotate(total_liberado=Sum("quantidade_liberada"))
        .order_by("-total_liberado")[:10]
    )

    chart_labels = [
        f"{m['material__codigo']} - {m['material__nome']}" for m in top_materiais
    ]
    chart_data = [m["total_liberado"] for m in top_materiais]

    context = {
        "materiais": materiais[:5],
        "total_materiais": total_materiais,
        "total_requisicoes": requisicoes.count(),
        "requisicoes_pendentes": pendentes,
        "requisicoes_negadas": negadas,
        "anos_disponiveis": anos_disponiveis,
        "ano_selecionado": ano_selecionado,
        "top_materiais": top_materiais,
        "chart_labels_json": json.dumps(chart_labels, ensure_ascii=False),
        "chart_data_json": json.dumps(chart_data),
    }
    return render(request, "core/dashboard.html", context)


def lista_materiais_publica(request):
    prefeitura_id, secretaria_id = _get_unidade_from_session(request)
    materiais = Material.objects.none()
    if prefeitura_id and secretaria_id:
        materiais = Material.objects.filter(
            prefeitura_id=prefeitura_id,
            secretaria_id=secretaria_id,
            ativo=True,
        )
    return render(
        request,
        "estoque/lista_materiais_publica.html",
        {"materiais": materiais},
    )


@login_required
def listar_materiais(request):
    if not _require_admin(request.user):
        return HttpResponseForbidden("Acesso restrito a administradores.")

    prefeitura_id, secretaria_id = _get_unidade_from_session(request)
    materiais = Material.objects.filter(
        prefeitura_id=prefeitura_id,
        secretaria_id=secretaria_id,
    )

    # Filtros
    buscar = (request.GET.get("buscar") or "").strip()
    categoria = (request.GET.get("categoria") or "").strip()
    ativo = (request.GET.get("ativo") or "").strip()

    if buscar:
        materiais = materiais.filter(
            Q(codigo__icontains=buscar)
            | Q(nome__icontains=buscar)
            | Q(marca__icontains=buscar)
            | Q(categoria__icontains=buscar)
        )

    if categoria and categoria in dict(CATEGORIA_MATERIAL_CHOICES):
        materiais = materiais.filter(categoria=categoria)

    if ativo == "1":
        materiais = materiais.filter(ativo=True)
    elif ativo == "0":
        materiais = materiais.filter(ativo=False)

    return render(
        request,
        "estoque/listar_materiais.html",
        {
            "materiais": materiais,
            "categorias": CATEGORIA_MATERIAL_CHOICES,
            "filtro_buscar": buscar,
            "filtro_categoria": categoria,
            "filtro_ativo": ativo,
        },
    )


@login_required
def cadastrar_material(request):
    if not _require_admin(request.user):
        return HttpResponseForbidden("Acesso restrito a administradores.")

    prefeitura_id, secretaria_id = _get_unidade_from_session(request)

    if request.method == "POST":
        form = MaterialForm(request.POST)
        if form.is_valid():
            material = form.save(commit=False)
            material.prefeitura_id = prefeitura_id
            material.secretaria_id = secretaria_id
            material.save()
            messages.success(request, "Material cadastrado com sucesso.")
            return redirect("estoque:listar_materiais")
    else:
        form = MaterialForm()

    return render(
        request,
        "estoque/cadastrar_material.html",
        {"form": form},
    )


@login_required
def editar_material(request, pk):
    if not _require_admin(request.user):
        return HttpResponseForbidden("Acesso restrito a administradores.")

    prefeitura_id, secretaria_id = _get_unidade_from_session(request)
    material = get_object_or_404(
        Material,
        pk=pk,
        prefeitura_id=prefeitura_id,
        secretaria_id=secretaria_id,
    )

    if request.method == "POST":
        form = MaterialForm(request.POST, instance=material)
        if form.is_valid():
            form.save()
            messages.success(request, "Material atualizado com sucesso.")
            return redirect("estoque:listar_materiais")
    else:
        form = MaterialForm(instance=material)

    return render(
        request,
        "estoque/editar_material.html",
        {"form": form, "material": material},
    )


@login_required
def nova_requisicao(request):
    if request.user.tipo not in ("FUNCIONARIO", "ADMINISTRADOR"):
        return HttpResponseForbidden(
            "Apenas funcionários e administradores podem criar requisições."
        )

    prefeitura_id, secretaria_id = _get_unidade_from_session(request)
    material_id = request.GET.get("material")

    if request.method == "POST":
        form = NovaRequisicaoForm(request.POST)
        materiais_ids = request.POST.getlist("materiais[]")
        quantidades = request.POST.getlist("quantidades[]")

        if form.is_valid():
            pairs = []
            for mat_id, qtd in zip(materiais_ids, quantidades):
                mat_id = (mat_id or "").strip()
                qtd = (qtd or "").strip()
                if not mat_id or not qtd:
                    continue
                try:
                    mat_id_int = int(mat_id)
                    qtd_int = int(qtd)
                except ValueError:
                    continue
                if qtd_int <= 0:
                    continue
                pairs.append((mat_id_int, qtd_int))

            if not pairs:
                messages.error(
                    request,
                    "Informe pelo menos um item com material e quantidade válida.",
                )
            else:
                requisicao = Requisicao.objects.create(
                    prefeitura_id=prefeitura_id,
                    secretaria_id=secretaria_id,
                    solicitante=request.user,
                    setor=getattr(request.user, "setor", None),
                )
                if not requisicao.numero_requisicao:
                    requisicao.numero_requisicao = _gerar_numero_requisicao(
                        requisicao.prefeitura,
                        requisicao.secretaria,
                        requisicao.solicitante,
                    )
                    requisicao.save(update_fields=["numero_requisicao"])

                total_itens = 0
                materiais_qs = Material.objects.filter(
                    prefeitura_id=prefeitura_id,
                    secretaria_id=secretaria_id,
                    ativo=True,
                    quantidade_estoque__gt=0,
                    pk__in=[p[0] for p in pairs],
                )
                materiais_map = {m.pk: m for m in materiais_qs}

                for mat_id_int, qtd_int in pairs:
                    material = materiais_map.get(mat_id_int)
                    if not material:
                        continue
                    ItemRequisicao.objects.create(
                        requisicao=requisicao,
                        material=material,
                        quantidade_solicitada=qtd_int,
                    )
                    total_itens += 1

                if total_itens == 0:
                    requisicao.delete()
                    messages.error(
                        request,
                        "Nenhum item válido foi encontrado para esta requisição.",
                    )
                else:
                    messages.success(request, "Requisição criada com sucesso.")
                    return redirect("estoque:listar_requisicoes")
    else:
        form = NovaRequisicaoForm()

    materiais = Material.objects.filter(
        prefeitura_id=prefeitura_id,
        secretaria_id=secretaria_id,
        ativo=True,
        quantidade_estoque__gt=0,
    ).order_by("nome")

    material_inicial = None
    if material_id:
        try:
            material_inicial = materiais.get(pk=material_id)
        except Material.DoesNotExist:
            material_inicial = None

    return render(
        request,
        "estoque/nova_requisicao.html",
        {
            "form": form,
            "materiais": materiais,
            "material_inicial": material_inicial,
        },
    )


@login_required
def listar_requisicoes(request):
    prefeitura_id, secretaria_id = _get_unidade_from_session(request)
    requisicoes = Requisicao.objects.filter(
        prefeitura_id=prefeitura_id,
        secretaria_id=secretaria_id,
    )

    status = (request.GET.get("status") or "").strip()
    if status in dict(STATUS_REQUISICAO_CHOICES):
        requisicoes = requisicoes.filter(status=status)

    buscar = (request.GET.get("buscar") or "").strip()
    data_inicio = (request.GET.get("data_inicio") or "").strip()
    data_fim = (request.GET.get("data_fim") or "").strip()

    if buscar:
        requisicoes = requisicoes.filter(
            Q(numero_requisicao__icontains=buscar)
            | Q(solicitante__nome_completo__icontains=buscar)
            | Q(solicitante__email__icontains=buscar)
        )

    if data_inicio:
        dt_inicio = parse_date(data_inicio)
        if dt_inicio:
            requisicoes = requisicoes.filter(data_criacao__date__gte=dt_inicio)

    if data_fim:
        dt_fim = parse_date(data_fim)
        if dt_fim:
            requisicoes = requisicoes.filter(data_criacao__date__lte=dt_fim)

    if request.user.tipo == "FUNCIONARIO":
        requisicoes = requisicoes.filter(solicitante=request.user)

    requisicoes = requisicoes.select_related("solicitante")

    return render(
        request,
        "estoque/listar_requisicoes.html",
        {
            "requisicoes": requisicoes,
            "status_choices": STATUS_REQUISICAO_CHOICES,
            "filtro_status": status,
            "filtro_buscar": buscar,
            "filtro_data_inicio": data_inicio,
            "filtro_data_fim": data_fim,
        },
    )


@login_required
def detalhar_requisicao(request, pk):
    prefeitura_id, secretaria_id = _get_unidade_from_session(request)
    requisicao = get_object_or_404(
        Requisicao,
        pk=pk,
        prefeitura_id=prefeitura_id,
        secretaria_id=secretaria_id,
    )

    # Se a requisição já tem data de entrega, não altera estoque nem data;
    # apenas garante que exista um recibo e redireciona para ele.
    if requisicao.data_entrega:
        recibo, _ = Recibo.objects.get_or_create(
            requisicao=requisicao,
            defaults={
                "prefeitura": requisicao.prefeitura,
                "secretaria": requisicao.secretaria,
                "emitido_por": request.user,
            },
        )
        messages.info(request, "Entrega já confirmada anteriormente.")
        return redirect("estoque:detalhe_recibo", pk=recibo.pk)
    itens = requisicao.itens.select_related("material")
    return render(
        request,
        "estoque/detalhar_requisicao.html",
        {"requisicao": requisicao, "itens": itens},
    )


@login_required
def analisar_requisicao(request, pk):
    if not _require_admin(request.user):
        return HttpResponseForbidden("Apenas administradores podem analisar requisições.")

    prefeitura_id, secretaria_id = _get_unidade_from_session(request)
    requisicao = get_object_or_404(
        Requisicao,
        pk=pk,
        prefeitura_id=prefeitura_id,
        secretaria_id=secretaria_id,
    )

    ItemFormSet = modelformset_factory(
        ItemRequisicao,
        form=ItemRequisicaoAnaliseForm,
        extra=0,
    )

    if request.method == "POST":
        form = AnalisarRequisicaoForm(request.POST, instance=requisicao)
        formset = ItemFormSet(
            request.POST,
            queryset=requisicao.itens.all(),
        )
        if form.is_valid() and formset.is_valid():
            requisicao = form.save(commit=False)
            requisicao.aprovado_por = request.user
            requisicao.data_aprovacao = timezone.now()

            for item_form in formset:
                item = item_form.instance
                if not item_form.cleaned_data:
                    continue
                liberar = item_form.cleaned_data.get("liberar_item")
                if liberar:
                    nova_qtd = item.quantidade_solicitada
                else:
                    # Usa o valor informado manualmente (podendo ser 0 ou parcial)
                    nova_qtd = item_form.cleaned_data.get("quantidade_liberada", 0) or 0

                # Garante que a quantidade liberada não seja negativa nem
                # maior que a quantidade solicitada.
                if nova_qtd < 0:
                    nova_qtd = 0
                if nova_qtd > item.quantidade_solicitada:
                    nova_qtd = item.quantidade_solicitada

                item.quantidade_liberada = nova_qtd
                item.save(update_fields=["quantidade_liberada"])

            # Define o status automaticamente com base nas quantidades
            # liberadas, exceto se a requisição já estiver marcada como ENTREGUE.
            if requisicao.status != "ENTREGUE":
                itens = requisicao.itens.all()
                if itens.exists():
                    all_zero = True
                    all_full = True
                    for item in itens:
                        if item.quantidade_liberada != 0:
                            all_zero = False
                        if not (
                            item.quantidade_liberada == item.quantidade_solicitada
                            and item.quantidade_solicitada > 0
                        ):
                            all_full = False

                    if all_zero:
                        requisicao.status = "NEGADA"
                    elif all_full:
                        requisicao.status = "APROVADA"
                    else:
                        requisicao.status = "APROVADA_PARCIAL"

            requisicao.save()

            messages.success(request, "Requisição analisada com sucesso.")
            return redirect("estoque:detalhar_requisicao", pk=requisicao.pk)
    else:
        form = AnalisarRequisicaoForm(instance=requisicao)
        formset = ItemFormSet(queryset=requisicao.itens.all())

    return render(
        request,
        "estoque/analisar_requisicao.html",
        {"form": form, "formset": formset, "requisicao": requisicao},
    )


@login_required
def confirmar_entrega(request, pk):
    if not _require_admin(request.user):
        return HttpResponseForbidden(
            "Apenas administradores podem confirmar a entrega."
        )

    prefeitura_id, secretaria_id = _get_unidade_from_session(request)
    requisicao = get_object_or_404(
        Requisicao,
        pk=pk,
        prefeitura_id=prefeitura_id,
        secretaria_id=secretaria_id,
    )

    if request.method == "POST":
        itens = requisicao.itens.select_related("material")
        for item in itens:
            if item.quantidade_liberada > 0:
                material = item.material
                disponivel = material.quantidade_estoque
                if disponivel <= 0:
                    item.quantidade_liberada = 0
                    item.save(update_fields=["quantidade_liberada"])
                    continue

                if item.quantidade_liberada > disponivel:
                    item.quantidade_liberada = disponivel
                    item.save(update_fields=["quantidade_liberada"])

                material.quantidade_estoque = max(disponivel - item.quantidade_liberada, 0)
                material.save(update_fields=["quantidade_estoque"])

        requisicao.data_entrega = timezone.now()
        requisicao.save()

        recibo, _ = Recibo.objects.get_or_create(
            requisicao=requisicao,
            defaults={
                "prefeitura": requisicao.prefeitura,
                "secretaria": requisicao.secretaria,
                "emitido_por": request.user,
            },
        )

        messages.success(request, "Entrega confirmada e recibo gerado.")
        return redirect("estoque:detalhe_recibo", pk=recibo.pk)

    itens = requisicao.itens.select_related("material")
    return render(
        request,
        "estoque/confirmar_entrega.html",
        {"requisicao": requisicao, "itens": itens},
    )


@login_required
def detalhe_recibo(request, pk):
    prefeitura_id, secretaria_id = _get_unidade_from_session(request)
    recibo = get_object_or_404(
        Recibo,
        pk=pk,
        prefeitura_id=prefeitura_id,
        secretaria_id=secretaria_id,
    )
    itens = recibo.requisicao.itens.select_related("material")
    return render(
        request,
        "estoque/recibo_detalhe.html",
        {"recibo": recibo, "itens": itens},
    )


@login_required
def novo_movimento_estoque(request):
    if not _require_admin(request.user):
        return HttpResponseForbidden(
            "Apenas administradores podem registrar movimentos de estoque."
        )

    prefeitura_id, secretaria_id = _get_unidade_from_session(request)

    if request.method == "POST":
        form = MovimentoEstoqueForm(
            request.POST,
            prefeitura_id=prefeitura_id,
            secretaria_id=secretaria_id,
        )
        if form.is_valid():
            movimento: MovimentoEstoque = form.save(commit=False)
            quantidade = movimento.quantidade
            if quantidade <= 0:
                form.add_error("quantidade", "Informe uma quantidade maior que zero.")
            else:
                movimento.prefeitura_id = prefeitura_id
                movimento.secretaria_id = secretaria_id
                movimento.usuario = request.user
                # Mantém como ajuste genérico
                movimento.tipo_negocio = "AJUSTE"

                # Validação simples para não deixar negativo
                material = movimento.material
                estoque_atual = material.quantidade_estoque
                if movimento.tipo in ("ENTRADA", "AJUSTE_POSITIVO"):
                    novo_estoque = estoque_atual + quantidade
                else:
                    novo_estoque = estoque_atual - quantidade

                if novo_estoque < 0:
                    form.add_error(
                        "quantidade",
                        "Este ajuste resultaria em estoque negativo.",
                    )
                else:
                    movimento.save()
                    movimento.aplicar_no_estoque()

                    messages.success(request, "Movimento de estoque registrado.")
                    return redirect("estoque:listar_materiais")
    else:
        form = MovimentoEstoqueForm(
            prefeitura_id=prefeitura_id,
            secretaria_id=secretaria_id,
        )

    return render(
        request,
        "estoque/novo_movimento_estoque.html",
        {"form": form},
    )


@login_required
def entrada_compra(request):
    """
    Entrada de materiais por compra (suprimento de fundo) com Nota Fiscal.
    Apenas administradores.
    """
    if not _require_admin(request.user):
        return HttpResponseForbidden(
            "Apenas administradores podem registrar entradas por compra.",
        )

    prefeitura_id, secretaria_id = _get_unidade_from_session(request)

    if request.method == "POST":
        doc_form = DocumentoEstoqueForm(request.POST, request.FILES)
        materiais_ids = request.POST.getlist("materiais[]")
        quantidades = request.POST.getlist("quantidades[]")
        valores_unitarios = request.POST.getlist("valores_unitarios[]")

        if doc_form.is_valid():
            itens_brutos = []
            for mat_id, qtd, vlr in zip(
                materiais_ids,
                quantidades,
                valores_unitarios,
            ):
                mat_id = (mat_id or "").strip()
                qtd = (qtd or "").strip()
                vlr = (vlr or "").strip()
                if not mat_id or not qtd:
                    continue
                try:
                    mat_id_int = int(mat_id)
                    qtd_int = int(qtd)
                except ValueError:
                    continue
                if qtd_int <= 0:
                    continue

                valor_decimal = None
                if vlr:
                    try:
                        # evita problemas de vírgula vs ponto
                        from decimal import Decimal

                        valor_decimal = Decimal(vlr.replace(",", "."))
                    except Exception:
                        valor_decimal = None

                itens_brutos.append((mat_id_int, qtd_int, valor_decimal))

            if not itens_brutos:
                messages.error(
                    request,
                    "Informe pelo menos um item com material e quantidade válida.",
                )
            else:
                documento = doc_form.save(commit=False)
                documento.prefeitura_id = prefeitura_id
                documento.secretaria_id = secretaria_id
                documento.created_by = request.user
                documento.save()

                materiais_qs = Material.objects.filter(
                    prefeitura_id=prefeitura_id,
                    secretaria_id=secretaria_id,
                    pk__in=[m[0] for m in itens_brutos],
                )
                materiais_map = {m.pk: m for m in materiais_qs}

                total_itens = 0
                for mat_id_int, qtd_int, valor_decimal in itens_brutos:
                    material = materiais_map.get(mat_id_int)
                    if not material:
                        continue

                    movimento = MovimentoEstoque(
                        prefeitura_id=prefeitura_id,
                        secretaria_id=secretaria_id,
                        material=material,
                        tipo="ENTRADA",
                        tipo_negocio="SUPRIMENTO_FUNDO",
                        quantidade=qtd_int,
                        valor_unitario=valor_decimal,
                        documento=documento,
                        usuario=request.user,
                        observacao=documento.descricao or "",
                    )
                    movimento.save()
                    movimento.aplicar_no_estoque()
                    total_itens += 1

                if total_itens == 0:
                    documento.delete()
                    messages.error(
                        request,
                        "Nenhum item válido foi encontrado para esta entrada.",
                    )
                else:
                    messages.success(
                        request,
                        "Entrada por suprimento de fundo registrada com sucesso.",
                    )
                    return redirect("estoque:listar_materiais")
    else:
        doc_form = DocumentoEstoqueForm(initial={"tipo": "NF"})

    materiais = Material.objects.filter(
        prefeitura_id=prefeitura_id,
        secretaria_id=secretaria_id,
        ativo=True,
    ).order_by("nome")

    return render(
        request,
        "estoque/entrada_compra.html",
        {
            "doc_form": doc_form,
            "materiais": materiais,
        },
    )


@login_required
def relatorio_entrega_material(request, pk):
    prefeitura_id, secretaria_id = _get_unidade_from_session(request)
    requisicao = get_object_or_404(
        Requisicao,
        pk=pk,
        prefeitura_id=prefeitura_id,
        secretaria_id=secretaria_id,
    )
    itens = requisicao.itens.select_related("material")

    # Data/hora de impressão para exibir no relatório
    agora = timezone.now()

    # Recibo (para identificar quem efetivamente registrou a entrega)
    recibo = Recibo.objects.filter(requisicao=requisicao).select_related(
        "emitido_por",
    ).first()

    # Consumo real (somatório das quantidades liberadas)
    total_consumo = sum(i.quantidade_liberada for i in itens)

    return render(
        request,
        "estoque/relatorio_entrega_material.html",
        {
            "requisicao": requisicao,
            "itens": itens,
            "agora": agora,
            "recibo": recibo,
            "total_consumo": total_consumo,
        },
    )


@login_required
def relatorio_movimento_materiais(request):
    """
    Relatório de movimento de materiais (Entradas x Saídas) por período.
    Apenas administradores podem acessar.
    """
    if not _require_admin(request.user):
        return HttpResponseForbidden(
            "Apenas administradores podem visualizar este relatório."
        )

    prefeitura_id, secretaria_id = _get_unidade_from_session(request)

    hoje = timezone.localdate()
    ano_atual = hoje.year
    # Período padrão: ano corrente
    data_inicio_str = request.GET.get("data_inicio") or f"{ano_atual}-01-01"
    data_fim_str = request.GET.get("data_fim") or hoje.isoformat()

    data_inicio = parse_date(data_inicio_str) or timezone.datetime(
        ano_atual,
        1,
        1,
    ).date()
    data_fim = parse_date(data_fim_str) or hoje

    if data_fim < data_inicio:
        data_fim = data_inicio

    # Materiais da unidade
    materiais = Material.objects.filter(
        prefeitura_id=prefeitura_id,
        secretaria_id=secretaria_id,
    ).order_by("nome")

    material_ids = list(materiais.values_list("id", flat=True))

    # Movimentos de estoque no período
    mov_qs = MovimentoEstoque.objects.filter(
        prefeitura_id=prefeitura_id,
        secretaria_id=secretaria_id,
        material_id__in=material_ids,
        data_movimento__date__gte=data_inicio,
        data_movimento__date__lte=data_fim,
    ).values("material_id", "tipo").annotate(total=Sum("quantidade"))

    entradas_map: dict[int, int] = defaultdict(int)
    ajustes_neg_map: dict[int, int] = defaultdict(int)

    for row in mov_qs:
        mid = row["material_id"]
        tipo = row["tipo"]
        total = row["total"] or 0
        if tipo in ("ENTRADA", "AJUSTE_POSITIVO"):
            entradas_map[mid] += total
        elif tipo == "AJUSTE_NEGATIVO":
            ajustes_neg_map[mid] += total

    # Saídas por requisições entregues no período
    saidas_qs = (
        ItemRequisicao.objects.filter(
            material_id__in=material_ids,
            requisicao__prefeitura_id=prefeitura_id,
            requisicao__secretaria_id=secretaria_id,
            requisicao__data_entrega__date__gte=data_inicio,
            requisicao__data_entrega__date__lte=data_fim,
        )
        .values("material_id")
        .annotate(total=Sum("quantidade_liberada"))
    )

    saidas_req_map: dict[int, int] = defaultdict(int)
    for row in saidas_qs:
        saidas_req_map[row["material_id"]] = row["total"] or 0

    # Monta estrutura por material
    linhas = []
    total_entradas = 0
    total_saidas = 0
    saldo_final_total = 0

    for material in materiais:
        mid = material.id
        entradas = entradas_map[mid]
        ajustes_neg = ajustes_neg_map[mid]
        saidas_req = saidas_req_map[mid]

        # Considera ajustes negativos como saídas
        saidas = saidas_req + ajustes_neg
        saldo_final = material.quantidade_estoque
        saldo_final_total += saldo_final

        # saldo_inicial = saldo_final - entradas + saídas
        saldo_inicial = saldo_final - entradas + saidas

        if saldo_inicial > 0:
            variacao_percentual = (
                (saldo_final - saldo_inicial) / saldo_inicial
            ) * 100
        else:
            variacao_percentual = None

        ruptura = (
            material.quantidade_minima is not None
            and saldo_final <= material.quantidade_minima
        )

        total_entradas += entradas
        total_saidas += saidas

        linhas.append(
            {
                "material": material,
                "entradas": entradas,
                "saidas": saidas,
                "saldo_inicial": saldo_inicial,
                "saldo_final": saldo_final,
                "variacao_percentual": variacao_percentual,
                "ruptura": ruptura,
            },
        )

    # Totais gerais
    saldo_inicial_total = saldo_final_total - total_entradas + total_saidas
    if saldo_inicial_total > 0:
        variacao_percentual_total = (
            (saldo_final_total - saldo_inicial_total) / saldo_inicial_total
        ) * 100
    else:
        variacao_percentual_total = None

    contexto = {
        "linhas": linhas,
        "data_inicio": data_inicio,
        "data_fim": data_fim,
        "total_entradas": total_entradas,
        "total_saidas": total_saidas,
        "saldo_final_total": saldo_final_total,
        "saldo_inicial_total": saldo_inicial_total,
        "variacao_percentual_total": variacao_percentual_total,
    }

    return render(
        request,
        "estoque/relatorio_movimento_materiais.html",
        contexto,
    )


@login_required
def relatorio_movimentacoes_estoque(request):
    """
    Relatório geral de movimentações de estoque (suprimento, empréstimos,
    devoluções e ajustes) em nível de linha de movimento.
    Apenas administradores podem acessar.
    """
    if not _require_admin(request.user):
        return HttpResponseForbidden(
            "Apenas administradores podem visualizar este relatório.",
        )

    prefeitura_id, secretaria_id = _get_unidade_from_session(request)

    hoje = timezone.localdate()
    ano_atual = hoje.year
    data_inicio_str = request.GET.get("data_inicio") or f"{ano_atual}-01-01"
    data_fim_str = request.GET.get("data_fim") or hoje.isoformat()

    data_inicio = parse_date(data_inicio_str) or timezone.datetime(
        ano_atual,
        1,
        1,
    ).date()
    data_fim = parse_date(data_fim_str) or hoje
    if data_fim < data_inicio:
        data_fim = data_inicio

    tipo_negocio = (request.GET.get("tipo_negocio") or "").strip()
    direcao = (request.GET.get("direcao") or "").strip()
    orgao_externo = (request.GET.get("orgao_externo") or "").strip()

    movimentos = (
        MovimentoEstoque.objects.filter(
            prefeitura_id=prefeitura_id,
            secretaria_id=secretaria_id,
            data_movimento__date__gte=data_inicio,
            data_movimento__date__lte=data_fim,
        )
        .select_related("material", "documento", "usuario")
        .order_by("-data_movimento")
    )

    if tipo_negocio in dict(MovimentoEstoque.TIPO_NEGOCIO_CHOICES):
        movimentos = movimentos.filter(tipo_negocio=tipo_negocio)

    if direcao == "entrada":
        movimentos = movimentos.filter(tipo__in=("ENTRADA", "AJUSTE_POSITIVO"))
    elif direcao == "saida":
        movimentos = movimentos.filter(tipo="AJUSTE_NEGATIVO")

    if orgao_externo:
        movimentos = movimentos.filter(orgao_externo=orgao_externo)

    # Totais simples
    total_entradas = movimentos.filter(
        tipo__in=("ENTRADA", "AJUSTE_POSITIVO"),
    ).aggregate(total=Sum("quantidade"))["total"] or 0
    total_saidas = movimentos.filter(tipo="AJUSTE_NEGATIVO").aggregate(
        total=Sum("quantidade"),
    )["total"] or 0
    total_movimentos = movimentos.count()

    contexto = {
        "movimentos": movimentos,
        "data_inicio": data_inicio,
        "data_fim": data_fim,
        "tipo_negocio": tipo_negocio,
        "direcao": direcao,
        "orgao_externo": orgao_externo,
        "total_entradas": total_entradas,
        "total_saidas": total_saidas,
        "total_movimentos": total_movimentos,
        "tipo_negocio_choices": MovimentoEstoque.TIPO_NEGOCIO_CHOICES,
        "orgao_externo_choices": ORGAO_EXTERNO_CHOICES,
    }

    return render(
        request,
        "estoque/relatorio_movimentacoes_estoque.html",
        contexto,
    )


@login_required
def relatorio_consumo_trienio_materiais(request):
    """
    Relatório estatístico de consumo por material nos três últimos anos
    (a partir de um ano de referência), com média anual para projeção.
    Usa sempre consumo real (quantidade liberada em requisições entregues).
    """
    if not _require_admin(request.user):
        return HttpResponseForbidden(
            "Apenas administradores podem visualizar este relatório.",
        )

    prefeitura_id, secretaria_id = _get_unidade_from_session(request)

    hoje = timezone.localdate()
    ano_atual = hoje.year

    # Anos disponíveis com base em requisições entregues
    anos_qs = (
        Requisicao.objects.filter(
            prefeitura_id=prefeitura_id,
            secretaria_id=secretaria_id,
            data_entrega__isnull=False,
        )
        .dates("data_entrega", "year")
    )
    anos_disponiveis = sorted([d.year for d in anos_qs]) or [ano_atual]

    ano_param = request.GET.get("ano")
    try:
        ano_referencia = int(ano_param) if ano_param else ano_atual
    except (TypeError, ValueError):
        ano_referencia = ano_atual

    if ano_referencia not in anos_disponiveis:
        ano_referencia = anos_disponiveis[-1]

    anos_periodo = [ano_referencia - 2, ano_referencia - 1, ano_referencia]

    # Itens de requisição entregues nos três anos do período
    itens_qs = ItemRequisicao.objects.filter(
        requisicao__prefeitura_id=prefeitura_id,
        requisicao__secretaria_id=secretaria_id,
        requisicao__data_entrega__year__in=anos_periodo,
        requisicao__data_entrega__isnull=False,
    )

    # Agrega consumo por material e por ano
    agregados = (
        itens_qs.annotate(ano=ExtractYear("requisicao__data_entrega"))
        .values(
            "material_id",
            "material__codigo",
            "material__nome",
            "ano",
        )
        .annotate(total=Sum("quantidade_liberada"))
    )

    # Monta estrutura: material -> {dados, consumo por ano}
    materiais_map: dict[int, dict] = {}
    for row in agregados:
        mid = row["material_id"]
        if mid not in materiais_map:
            materiais_map[mid] = {
                "codigo": row["material__codigo"],
                "nome": row["material__nome"],
                "por_ano": {a: 0 for a in anos_periodo},
            }
        ano = row["ano"]
        if ano in materiais_map[mid]["por_ano"]:
            materiais_map[mid]["por_ano"][ano] += row["total"] or 0

    linhas = []
    total_por_ano = {a: 0 for a in anos_periodo}

    for data in materiais_map.values():
        por_ano = data["por_ano"]
        total_tri = sum(por_ano[a] for a in anos_periodo)
        media = total_tri / 3 if total_tri else 0

        for a in anos_periodo:
            total_por_ano[a] += por_ano[a]

        linhas.append(
            {
                "codigo": data["codigo"],
                "nome": data["nome"],
                "consumo_ano1": por_ano[anos_periodo[0]],
                "consumo_ano2": por_ano[anos_periodo[1]],
                "consumo_ano3": por_ano[anos_periodo[2]],
                "media": media,
                "total_trienio": total_tri,
            },
        )

    # Ordena pelo maior consumo no triénio
    linhas.sort(key=lambda x: x["total_trienio"], reverse=True)

    contexto = {
        "ano_referencia": ano_referencia,
        "anos_periodo": anos_periodo,
        "anos_disponiveis": anos_disponiveis,
        "linhas": linhas,
        "total_por_ano": total_por_ano,
    }

    return render(
        request,
        "estoque/relatorio_consumo_trienio_materiais.html",
        contexto,
    )


@login_required
def relatorio_requisicoes_status(request):
    """
    Relatório de requisições por status (pendentes, aprovadas, etc.).
    Apenas administradores podem acessar.
    """
    if not _require_admin(request.user):
        return HttpResponseForbidden(
            "Apenas administradores podem visualizar este relatório."
        )

    prefeitura_id, secretaria_id = _get_unidade_from_session(request)

    hoje = timezone.localdate()
    ano_atual = hoje.year

    data_inicio_str = request.GET.get("data_inicio") or f"{ano_atual}-01-01"
    data_fim_str = request.GET.get("data_fim") or hoje.isoformat()

    data_inicio = parse_date(data_inicio_str) or timezone.datetime(
        ano_atual,
        1,
        1,
    ).date()
    data_fim = parse_date(data_fim_str) or hoje

    if data_fim < data_inicio:
        data_fim = data_inicio

    qs = Requisicao.objects.filter(
        prefeitura_id=prefeitura_id,
        secretaria_id=secretaria_id,
        data_criacao__date__gte=data_inicio,
        data_criacao__date__lte=data_fim,
    )

    total = qs.count()

    resumo_status = []
    # Contagem por status "lógico" (sem ENTREGUE)
    status_logicos = [s for s in STATUS_REQUISICAO_CHOICES if s[0] != "ENTREGUE"]
    for codigo, label in status_logicos:
        qtd = qs.filter(status=codigo).count()
        if total > 0:
            percentual = (qtd / total) * 100
        else:
            percentual = 0
        resumo_status.append(
            {
                "codigo": codigo,
                "label": label,
                "quantidade": qtd,
                "percentual": percentual,
            },
        )

    # Linha separada para ENTREGUE: qualquer status com data_entrega preenchida
    entregues_qtd = qs.filter(data_entrega__isnull=False).count()
    if total > 0:
        entregues_percentual = (entregues_qtd / total) * 100
    else:
        entregues_percentual = 0

    resumo_status.append(
        {
            "codigo": "ENTREGUE",
            "label": "Entregue",
            "quantidade": entregues_qtd,
            "percentual": entregues_percentual,
        },
    )

    contexto = {
        "data_inicio": data_inicio,
        "data_fim": data_fim,
        "total": total,
        "resumo_status": resumo_status,
    }

    return render(
        request,
        "estoque/relatorio_requisicoes_status.html",
        contexto,
    )


@login_required
def relatorio_consumo_categoria(request):
    """
    Relatório de consumo por categoria:
    - Total consumido por categoria no ano selecionado
    - Consumo mensal por categoria
    - Curva ABC de consumo
    """
    if not _require_admin(request.user):
        return HttpResponseForbidden(
            "Apenas administradores podem visualizar este relatório."
        )

    prefeitura_id, secretaria_id = _get_unidade_from_session(request)

    hoje = timezone.localdate()
    ano_atual = hoje.year

    # Anos disponíveis com base nas requisições entregues
    anos_qs = (
        Requisicao.objects.filter(
            prefeitura_id=prefeitura_id,
            secretaria_id=secretaria_id,
            data_entrega__isnull=False,
        )
        .dates("data_entrega", "year")
    )
    anos_disponiveis = [d.year for d in anos_qs] or [ano_atual]

    ano_param = request.GET.get("ano")
    try:
        ano_selecionado = int(ano_param) if ano_param else ano_atual
    except (TypeError, ValueError):
        ano_selecionado = ano_atual

    if ano_selecionado not in anos_disponiveis:
        ano_selecionado = anos_disponiveis[-1]

    # Itens de requisição entregues no ano selecionado
    itens_qs = ItemRequisicao.objects.filter(
        requisicao__prefeitura_id=prefeitura_id,
        requisicao__secretaria_id=secretaria_id,
        requisicao__data_entrega__year=ano_selecionado,
        requisicao__data_entrega__isnull=False,
    )

    # Total consumido por categoria
    totais_cat_qs = (
        itens_qs.values("material__categoria")
        .annotate(total=Sum("quantidade_liberada"))
        .order_by("-total")
    )

    # Consumo mensal por categoria
    mensal_qs = (
        itens_qs.annotate(mes=ExtractMonth("requisicao__data_entrega"))
        .values("material__categoria", "mes")
        .annotate(total=Sum("quantidade_liberada"))
    )

    # Mapa categoria -> [12 meses]
    consumo_mensal: dict[str, list[int]] = defaultdict(
        lambda: [0] * 12,
    )
    for row in mensal_qs:
        cat = row["material__categoria"] or ""
        mes = row["mes"] or 0
        if 1 <= mes <= 12:
            consumo_mensal[cat][mes - 1] += row["total"] or 0

    # Curva ABC
    categoria_labels = dict(CATEGORIA_MATERIAL_CHOICES)
    linhas = []
    total_geral = 0
    for row in totais_cat_qs:
        cat = row["material__categoria"] or ""
        total = row["total"] or 0
        total_geral += total
        linhas.append(
            {
                "codigo": cat,
                "label": categoria_labels.get(cat, cat or "Sem categoria"),
                "total": total,
                "mensal": consumo_mensal.get(cat, [0] * 12),
            },
        )

    # Ordena por total desc. (já vem assim) e calcula percentuais e classes ABC
    cumulativo = 0
    for linha in linhas:
        if total_geral > 0:
            perc = (linha["total"] / total_geral) * 100
        else:
            perc = 0
        linha["percentual"] = perc

    # Recalcula com cumulativo para ABC
    linhas_ordenadas = sorted(linhas, key=lambda x: x["total"], reverse=True)
    cumulativo_perc = 0
    for linha in linhas_ordenadas:
        if total_geral > 0:
            perc = (linha["total"] / total_geral) * 100
        else:
            perc = 0
        cumulativo_perc += perc
        linha["percentual_acumulado"] = cumulativo_perc
        if cumulativo_perc <= 80:
            classe = "A"
        elif cumulativo_perc <= 95:
            classe = "B"
        else:
            classe = "C"
        linha["classe_abc"] = classe

    contexto = {
        "ano_selecionado": ano_selecionado,
        "anos_disponiveis": anos_disponiveis,
        "linhas": linhas_ordenadas,
        "total_geral": total_geral,
    }

    return render(
        request,
        "estoque/relatorio_consumo_categoria.html",
        contexto,
    )


@login_required
def relatorio_requisicoes_periodo(request):
    """
    Relatório de requisições por período (diário, semanal, mensal, anual),
    com gráfico de barras e linha de consumo (sazonalidade).
    """
    if not _require_admin(request.user):
        return HttpResponseForbidden(
            "Apenas administradores podem visualizar este relatório."
        )

    prefeitura_id, secretaria_id = _get_unidade_from_session(request)

    hoje = timezone.localdate()
    ano_atual = hoje.year

    data_inicio_str = request.GET.get("data_inicio") or f"{ano_atual}-01-01"
    data_fim_str = request.GET.get("data_fim") or hoje.isoformat()
    agrupamento = (request.GET.get("agrupamento") or "mensal").lower()

    data_inicio = parse_date(data_inicio_str) or timezone.datetime(
        ano_atual,
        1,
        1,
    ).date()
    data_fim = parse_date(data_fim_str) or hoje

    if data_fim < data_inicio:
        data_fim = data_inicio

    # Define função de truncamento e formatação de rótulo
    if agrupamento == "diario":
        trunc_fn_req = TruncDate("data_criacao")
        trunc_fn_cons = TruncDate("requisicao__data_entrega")

        def format_label(d):
            return d.strftime("%d/%m/%Y")

    elif agrupamento == "semanal":
        trunc_fn_req = TruncWeek("data_criacao")
        trunc_fn_cons = TruncWeek("requisicao__data_entrega")

        def format_label(d):
            # Mostra semana iniciando na data truncada
            return f"Semana de {d.strftime('%d/%m/%Y')}"

    elif agrupamento == "anual":
        trunc_fn_req = TruncYear("data_criacao")
        trunc_fn_cons = TruncYear("requisicao__data_entrega")

        def format_label(d):
            return d.strftime("%Y")

    else:  # mensal (padrão)
        agrupamento = "mensal"
        trunc_fn_req = TruncMonth("data_criacao")
        trunc_fn_cons = TruncMonth("requisicao__data_entrega")

        def format_label(d):
            return d.strftime("%m/%Y")

    # Requisições no período (por data de criação)
    req_qs = (
        Requisicao.objects.filter(
            prefeitura_id=prefeitura_id,
            secretaria_id=secretaria_id,
            data_criacao__date__gte=data_inicio,
            data_criacao__date__lte=data_fim,
        )
        .annotate(periodo=trunc_fn_req)
        .values("periodo")
        .annotate(qtd=Count("id"))
    )

    # Consumo real (somente requisições entregues, por data de entrega)
    cons_qs = (
        ItemRequisicao.objects.filter(
            requisicao__prefeitura_id=prefeitura_id,
            requisicao__secretaria_id=secretaria_id,
            requisicao__data_entrega__date__gte=data_inicio,
            requisicao__data_entrega__date__lte=data_fim,
            requisicao__data_entrega__isnull=False,
        )
        .annotate(periodo=trunc_fn_cons)
        .values("periodo")
        .annotate(consumo=Sum("quantidade_liberada"))
    )

    qtd_map: dict = {}
    for row in req_qs:
        qtd_map[row["periodo"]] = row["qtd"] or 0

    cons_map: dict = {}
    for row in cons_qs:
        cons_map[row["periodo"]] = row["consumo"] or 0

    # Junta todos os períodos observados
    periodos = set(qtd_map.keys()) | set(cons_map.keys())
    periodos = sorted([p for p in periodos if p is not None])

    labels = [format_label(p) for p in periodos]
    dados_qtd = [qtd_map.get(p, 0) for p in periodos]
    dados_consumo = [cons_map.get(p, 0) for p in periodos]

    total_requisicoes = sum(dados_qtd)
    total_consumo = sum(dados_consumo)

    # Série combinada para facilitar exibição na tabela
    series = []
    for label, qtd, cons in zip(labels, dados_qtd, dados_consumo):
        series.append(
            {
                "label": label,
                "qtd": qtd,
                "consumo": cons,
            },
        )

    contexto = {
        "data_inicio": data_inicio,
        "data_fim": data_fim,
        "agrupamento": agrupamento,
        "labels": labels,
        "dados_qtd": dados_qtd,
        "dados_consumo": dados_consumo,
        "series": series,
        "total_requisicoes": total_requisicoes,
        "total_consumo": total_consumo,
    }

    return render(
        request,
        "estoque/relatorio_requisicoes_periodo.html",
        contexto,
    )


@login_required
def relatorio_consumo_usuario(request):
    """
    Relatório de consumo por usuário:
    - ranking de quem mais consome
    - consumo mês a mês
    - indicação simples de consumo acima da média
    """
    if not _require_admin(request.user):
        return HttpResponseForbidden(
            "Apenas administradores podem visualizar este relatório."
        )

    prefeitura_id, secretaria_id = _get_unidade_from_session(request)

    hoje = timezone.localdate()
    ano_atual = hoje.year

    # Anos disponíveis com base nas requisições entregues
    anos_qs = (
        Requisicao.objects.filter(
            prefeitura_id=prefeitura_id,
            secretaria_id=secretaria_id,
            data_entrega__isnull=False,
        )
        .dates("data_entrega", "year")
    )
    anos_disponiveis = [d.year for d in anos_qs] or [ano_atual]

    ano_param = request.GET.get("ano")
    try:
        ano_selecionado = int(ano_param) if ano_param else ano_atual
    except (TypeError, ValueError):
        ano_selecionado = ano_atual

    if ano_selecionado not in anos_disponiveis:
        ano_selecionado = anos_disponiveis[-1]

    # Itens de requisição entregues no ano selecionado (consumo real)
    # Considera qualquer usuário como solicitante (ADMINISTRADOR ou FUNCIONARIO)
    itens_qs = ItemRequisicao.objects.filter(
        requisicao__prefeitura_id=prefeitura_id,
        requisicao__secretaria_id=secretaria_id,
        requisicao__data_entrega__year=ano_selecionado,
        requisicao__data_entrega__isnull=False,
    )

    # Total por usuário
    total_por_usuario_qs = (
        itens_qs.values(
            "requisicao__solicitante_id",
            "requisicao__solicitante__nome_completo",
            "requisicao__solicitante__matricula",
            "requisicao__solicitante__setor__nome",
        )
        .annotate(total=Sum("quantidade_liberada"))
        .order_by("-total")
    )

    # Consumo mensal por usuário
    mensal_qs = (
        itens_qs.annotate(mes=ExtractMonth("requisicao__data_entrega"))
        .values("requisicao__solicitante_id", "mes")
        .annotate(total=Sum("quantidade_liberada"))
    )

    consumo_mensal: dict[int, list[int]] = defaultdict(lambda: [0] * 12)
    for row in mensal_qs:
        uid = row["requisicao__solicitante_id"]
        mes = row["mes"] or 0
        if 1 <= mes <= 12:
            consumo_mensal[uid][mes - 1] += row["total"] or 0

    usuarios = []
    total_geral = 0

    for row in total_por_usuario_qs:
        uid = row["requisicao__solicitante_id"]
        total = row["total"] or 0
        total_geral += total
        usuarios.append(
            {
                "id": uid,
                "nome": row["requisicao__solicitante__nome_completo"],
                "matricula": row["requisicao__solicitante__matricula"],
                "setor": row["requisicao__solicitante__setor__nome"],
                "total": total,
                "mensal": consumo_mensal.get(uid, [0] * 12),
            },
        )

    # Calcula percentual e identifica consumo acima da média
    media_consumo = (total_geral / len(usuarios)) if usuarios else 0
    for u in usuarios:
        if total_geral > 0:
            u["percentual"] = (u["total"] / total_geral) * 100
        else:
            u["percentual"] = 0

        if media_consumo > 0 and u["total"] >= media_consumo * 2:
            u["status_consumo"] = "Acima da média"
        else:
            u["status_consumo"] = "Dentro da faixa esperada"

    # Ranking já está ordenado por total desc.
    ranking = usuarios

    # Dados para gráfico: top 10 consumidores
    top10 = ranking[:10]
    chart_labels = [u["nome"] for u in top10]
    chart_data = [u["total"] for u in top10]

    contexto = {
        "ano_selecionado": ano_selecionado,
        "anos_disponiveis": anos_disponiveis,
        "usuarios": ranking,
        "total_geral": total_geral,
        "media_consumo": media_consumo,
        "chart_labels_json": json.dumps(chart_labels, ensure_ascii=False),
        "chart_data_json": json.dumps(chart_data),
    }

    return render(
        request,
        "estoque/relatorio_consumo_usuario.html",
        contexto,
    )


@login_required
def relatorio_consumo_setor(request):
    """
    Relatório de consumo por setor:
    - ranking de setores que mais consomem
    - materiais mais usados por setor
    """
    if not _require_admin(request.user):
        return HttpResponseForbidden(
            "Apenas administradores podem visualizar este relatório."
        )

    prefeitura_id, secretaria_id = _get_unidade_from_session(request)

    hoje = timezone.localdate()
    ano_atual = hoje.year

    # Anos disponíveis com base em requisições entregues
    anos_qs = (
        Requisicao.objects.filter(
            prefeitura_id=prefeitura_id,
            secretaria_id=secretaria_id,
            data_entrega__isnull=False,
        )
        .dates("data_entrega", "year")
    )
    anos_disponiveis = [d.year for d in anos_qs] or [ano_atual]

    ano_param = request.GET.get("ano")
    try:
        ano_selecionado = int(ano_param) if ano_param else ano_atual
    except (TypeError, ValueError):
        ano_selecionado = ano_atual

    if ano_selecionado not in anos_disponiveis:
        ano_selecionado = anos_disponiveis[-1]

    # Itens de requisição entregues no ano selecionado, com setor definido
    itens_qs = ItemRequisicao.objects.filter(
        requisicao__prefeitura_id=prefeitura_id,
        requisicao__secretaria_id=secretaria_id,
        requisicao__data_entrega__year=ano_selecionado,
        requisicao__data_entrega__isnull=False,
        requisicao__setor__isnull=False,
    )

    # Total por setor
    total_por_setor_qs = (
        itens_qs.values(
            "requisicao__setor_id",
            "requisicao__setor__nome",
            "requisicao__setor__secretaria__sigla",
        )
        .annotate(total=Sum("quantidade_liberada"))
        .order_by("-total")
    )

    # Materiais mais consumidos por setor
    mats_por_setor_qs = (
        itens_qs.values(
            "requisicao__setor_id",
            "requisicao__setor__nome",
            "material__codigo",
            "material__nome",
        )
        .annotate(total=Sum("quantidade_liberada"))
        .order_by("requisicao__setor__nome", "-total")
    )

    top_mats_map: dict[int, list[dict]] = defaultdict(list)
    for row in mats_por_setor_qs:
        setor_id = row["requisicao__setor_id"]
        if len(top_mats_map[setor_id]) >= 5:
            continue
        top_mats_map[setor_id].append(
            {
                "codigo": row["material__codigo"],
                "nome": row["material__nome"],
                "total": row["total"] or 0,
            },
        )

    setores = []
    total_geral = 0
    for row in total_por_setor_qs:
        sid = row["requisicao__setor_id"]
        total = row["total"] or 0
        total_geral += total
        setores.append(
            {
                "id": sid,
                "nome": row["requisicao__setor__nome"],
                "sigla_secretaria": row["requisicao__setor__secretaria__sigla"],
                "total": total,
                "top_materiais": top_mats_map.get(sid, []),
            },
        )

    # Calcula percentual e identifica setor de maior impacto (topo do ranking)
    for s in setores:
        if total_geral > 0:
            s["percentual"] = (s["total"] / total_geral) * 100
        else:
            s["percentual"] = 0

    ranking = setores
    setor_top = ranking[0] if ranking else None

    # Dados para gráfico: top 10 setores
    top10 = ranking[:10]
    chart_labels = [s["nome"] for s in top10]
    chart_data = [s["total"] for s in top10]

    contexto = {
        "ano_selecionado": ano_selecionado,
        "anos_disponiveis": anos_disponiveis,
        "setores": ranking,
        "total_geral": total_geral,
        "setor_top": setor_top,
        "chart_labels_json": json.dumps(chart_labels, ensure_ascii=False),
        "chart_data_json": json.dumps(chart_data),
    }

    return render(
        request,
        "estoque/relatorio_consumo_setor.html",
        contexto,
    )

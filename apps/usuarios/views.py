from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render

from apps.cadastros.models import Prefeitura, Secretaria

from .forms import LoginForm


def login_view(request):
    if request.user.is_authenticated:
        return redirect("estoque:dashboard")

    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            password = form.cleaned_data["password"]
            codigo_ibge = form.cleaned_data["codigo_ibge"]
            secretaria = form.cleaned_data["secretaria"]

            try:
                prefeitura = Prefeitura.objects.get(
                    codigo_ibge=codigo_ibge,
                    ativo=True,
                )
            except Prefeitura.DoesNotExist:
                form.add_error(
                    "codigo_ibge",
                    "Prefeitura não encontrada ou inativa para o código informado.",
                )
            else:
                if secretaria.prefeitura_id != prefeitura.id:
                    form.add_error(
                        "secretaria",
                        "A secretaria selecionada não pertence à prefeitura informada.",
                    )
                else:
                    usuario = authenticate(
                        request,
                        email=email,
                        password=password,
                    )

                    if usuario is None:
                        messages.error(request, "Credenciais inválidas.")
                    elif not usuario.ativo:
                        messages.error(request, "Usuário inativo.")
                    elif (
                        usuario.prefeitura_id != prefeitura.id
                        or usuario.secretaria_id != secretaria.id
                    ):
                        messages.error(
                            request,
                            "Prefeitura ou secretaria não conferem com o usuário.",
                        )
                    else:
                        login(request, usuario)
                        request.session["prefeitura_id"] = prefeitura.id
                        request.session["secretaria_id"] = secretaria.id
                        return redirect("estoque:dashboard")
    else:
        form = LoginForm()

    return render(request, "usuarios/login.html", {"form": form})


def secretarias_por_ibge(request):
    codigo_ibge = (request.GET.get("codigo_ibge") or "").strip()
    secretarias_data: list[dict] = []

    if codigo_ibge:
        qs = Secretaria.objects.filter(
            prefeitura__codigo_ibge=codigo_ibge,
            prefeitura__ativo=True,
            ativo=True,
        ).order_by("nome")
        secretarias_data = [
            {"id": s.id, "nome": s.nome, "sigla": s.sigla} for s in qs
        ]

    return JsonResponse({"secretarias": secretarias_data})


def logout_view(request):
    logout(request)
    request.session.flush()
    return redirect("usuarios:login")


@login_required
def perfil_view(request):
    return render(request, "usuarios/perfil.html")

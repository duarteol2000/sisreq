from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .models import Prefeitura, Secretaria


@login_required
def listar_prefeituras(request):
    prefeituras = Prefeitura.objects.all()
    return render(
        request,
        "cadastros/listar_prefeituras.html",
        {"prefeituras": prefeituras},
    )


@login_required
def listar_secretarias(request):
    secretarias = Secretaria.objects.select_related("prefeitura").all()
    return render(
        request,
        "cadastros/listar_secretarias.html",
        {"secretarias": secretarias},
    )


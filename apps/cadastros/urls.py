from django.urls import path

from . import views

app_name = "cadastros"

urlpatterns = [
    path("prefeituras/", views.listar_prefeituras, name="listar_prefeituras"),
    path("secretarias/", views.listar_secretarias, name="listar_secretarias"),
]


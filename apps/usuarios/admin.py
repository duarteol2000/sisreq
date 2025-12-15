from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    model = Usuario
    ordering = ("email",)
    list_display = (
        "email",
        "nome_completo",
        "matricula",
        "prefeitura",
        "secretaria",
        "setor",
        "tipo",
        "ativo",
    )
    search_fields = ("email", "nome_completo", "matricula")
    list_filter = ("prefeitura", "secretaria", "setor", "tipo", "ativo")

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            "Informações pessoais",
            {
                "fields": (
                    "nome_completo",
                    "matricula",
                    "prefeitura",
                    "secretaria",
                    "setor",
                    "tipo",
                )
            },
        ),
        (
            "Permissões",
            {
                "fields": (
                    "ativo",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Datas importantes", {"fields": ("last_login",)}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "nome_completo",
                    "matricula",
                    "prefeitura",
                    "secretaria",
                    "setor",
                    "tipo",
                    "password1",
                    "password2",
                    "is_staff",
                    "is_superuser",
                    "ativo",
                ),
            },
        ),
    )

    filter_horizontal = ("groups", "user_permissions")

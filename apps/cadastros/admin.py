from django.contrib import admin
from django import forms

from .models import Prefeitura, Secretaria, Setor


@admin.register(Prefeitura)
class PrefeituraAdmin(admin.ModelAdmin):
    list_display = ("nome", "sigla", "codigo_ibge", "ativo")
    search_fields = ("nome", "sigla", "codigo_ibge")
    list_filter = ("ativo",)


@admin.register(Secretaria)
class SecretariaAdmin(admin.ModelAdmin):
    list_display = ("nome", "sigla", "prefeitura", "ativo")
    search_fields = ("nome", "sigla")
    list_filter = ("prefeitura", "ativo")


@admin.register(Setor)
class SetorAdmin(admin.ModelAdmin):
    class SetorAdminForm(forms.ModelForm):
        prefeitura = forms.ModelChoiceField(
            queryset=Prefeitura.objects.filter(ativo=True),
            required=True,
            label="Prefeitura",
        )

        class Meta:
            model = Setor
            fields = "__all__"

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)

            # queryset base: todas secretarias ativas
            qs = Secretaria.objects.filter(ativo=True)

            # Se a prefeitura veio no POST, filtra secretarias por ela
            if "prefeitura" in self.data:
                try:
                    prefeitura_id = int(self.data.get("prefeitura"))
                    qs = qs.filter(prefeitura_id=prefeitura_id)
                except (TypeError, ValueError):
                    pass
            # Se estamos editando um setor existente, usa a prefeitura da secretaria atual
            elif self.instance.pk and self.instance.secretaria_id:
                prefeitura = self.instance.secretaria.prefeitura
                self.fields["prefeitura"].initial = prefeitura
                qs = qs.filter(prefeitura=prefeitura)

            self.fields["secretaria"].queryset = qs

    form = SetorAdminForm
    # Ordem dos campos no admin: Prefeitura, Secretaria, depois demais campos
    fields = ("prefeitura", "secretaria", "nome", "sigla", "ativo")
    list_display = ("nome", "sigla", "secretaria", "ativo")
    search_fields = ("nome", "sigla")
    list_filter = ("secretaria", "ativo")

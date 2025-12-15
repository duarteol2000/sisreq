from django import forms

from .models import Prefeitura, Secretaria


class PrefeituraForm(forms.ModelForm):
    class Meta:
        model = Prefeitura
        fields = ["nome", "sigla", "codigo_ibge", "ativo"]


class SecretariaForm(forms.ModelForm):
    class Meta:
        model = Secretaria
        fields = ["prefeitura", "nome", "sigla", "ativo"]


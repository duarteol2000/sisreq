from django import forms

from apps.cadastros.models import Secretaria


class LoginForm(forms.Form):
    email = forms.EmailField(label="E-mail")
    password = forms.CharField(label="Senha", widget=forms.PasswordInput)
    codigo_ibge = forms.CharField(label="Código IBGE da Prefeitura")
    secretaria = forms.ModelChoiceField(
        queryset=Secretaria.objects.none(),
        label="Secretaria",
    )

    field_order = ["codigo_ibge", "secretaria", "email", "password"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Classes padrão dos inputs
        self.fields["email"].widget.attrs.setdefault("class", "form-control")
        self.fields["password"].widget.attrs.setdefault("class", "form-control")
        self.fields["codigo_ibge"].widget.attrs.setdefault(
            "class", "form-control js-int"
        )
        self.fields["secretaria"].widget.attrs.setdefault("class", "form-select")

        codigo_ibge_value = (
            self.data.get("codigo_ibge") or self.initial.get("codigo_ibge")
        )
        if codigo_ibge_value:
            self.fields["secretaria"].queryset = Secretaria.objects.filter(
                prefeitura__codigo_ibge=codigo_ibge_value,
                prefeitura__ativo=True,
                ativo=True,
            )


class PerfilForm(forms.ModelForm):
    class Meta:
        model = Secretaria  # placeholder to avoid empty file; not used for save
        fields: list[str] = []

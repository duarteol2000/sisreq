from django.db import models


class Prefeitura(models.Model):
    nome = models.CharField(max_length=150)
    sigla = models.CharField(max_length=20)
    codigo_ibge = models.CharField(max_length=10, blank=True, null=True)
    ativo = models.BooleanField(default=True)
    logo = models.ImageField(
        upload_to="prefeituras",
        blank=True,
        null=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Prefeitura"
        verbose_name_plural = "Prefeituras"

    def __str__(self) -> str:
        return f"{self.nome} ({self.sigla})"


class Secretaria(models.Model):
    prefeitura = models.ForeignKey(
        Prefeitura,
        on_delete=models.PROTECT,
        related_name="secretarias",
    )
    nome = models.CharField(max_length=150)
    sigla = models.CharField(max_length=20)
    ativo = models.BooleanField(default=True)
    logo = models.ImageField(
        upload_to="secretarias",
        blank=True,
        null=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Secretaria"
        verbose_name_plural = "Secretarias"

    def __str__(self) -> str:
        if self.prefeitura_id:
            return f"{self.nome} ({self.sigla}) - {self.prefeitura.sigla}"
        return f"{self.nome} ({self.sigla})"


class Setor(models.Model):
    secretaria = models.ForeignKey(
        Secretaria,
        on_delete=models.PROTECT,
        related_name="setores",
    )
    nome = models.CharField(max_length=150)
    sigla = models.CharField(max_length=20)
    ativo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Setor"
        verbose_name_plural = "Setores"

    def __str__(self) -> str:
        return f"{self.nome} ({self.sigla})"

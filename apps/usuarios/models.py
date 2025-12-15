from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone

from apps.utils.choice import TIPO_USUARIO_CHOICES

from .managers import UsuarioManager


class Usuario(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    nome_completo = models.CharField(max_length=150)
    matricula = models.CharField(max_length=30, blank=True, null=True)
    prefeitura = models.ForeignKey(
        "cadastros.Prefeitura",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    secretaria = models.ForeignKey(
        "cadastros.Secretaria",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    setor = models.ForeignKey(
        "cadastros.Setor",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    tipo = models.CharField(
        max_length=20,
        choices=TIPO_USUARIO_CHOICES,
        default="FUNCIONARIO",
    )
    ativo = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["nome_completo"]

    objects = UsuarioManager()

    class Meta:
        verbose_name = "Usuário"
        verbose_name_plural = "Usuários"

    def __str__(self) -> str:
        return self.email or self.nome_completo

    @property
    def is_active(self) -> bool:
        return self.ativo

    @is_active.setter
    def is_active(self, value: bool) -> None:
        self.ativo = value

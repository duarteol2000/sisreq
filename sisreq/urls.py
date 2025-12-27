from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path(
        "usuarios/",
        include(("apps.usuarios.urls", "usuarios"), namespace="usuarios"),
    ),
    path(
        "",
        include(("apps.estoque.urls", "estoque"), namespace="estoque"),
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    # Em produção servimos mídia diretamente pelo Django (pequeno porte).
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

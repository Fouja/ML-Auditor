"""
URL configuration for ML-Auditor project.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path

from config.api import api


def health(request):
    """Liveness/readiness probe for Kubernetes, docker-compose, and the desktop app."""
    return JsonResponse({"status": "ok", "service": "ml-auditor-backend"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", api.urls),
    path("api/logs/", include("apps.logs.urls")),
    path("api/health/", health),
    path("health", health),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

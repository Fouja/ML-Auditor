from django.urls import path

from .views import ingest_frontend_logs

urlpatterns = [
    path("", ingest_frontend_logs, name="ingest-logs"),
]

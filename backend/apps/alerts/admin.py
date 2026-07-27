"""
Django admin configuration for AgentAlert model.
"""

from django.contrib import admin

from .models import AgentAlert


@admin.register(AgentAlert)
class AgentAlertAdmin(admin.ModelAdmin):
    model = AgentAlert
    list_display = (
        "id",
        "user",
        "title",
        "severity",
        "status",
        "source_type",
        "created_at",
    )
    list_filter = ("severity", "status", "source_type", "created_at")
    search_fields = ("title", "description", "user__email")
    readonly_fields = ("created_at", "updated_at", "acknowledged_at", "executed_at")
    ordering = ("-created_at",)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if not request.user.is_superuser:
            queryset = queryset.filter(user=request.user)
        return queryset

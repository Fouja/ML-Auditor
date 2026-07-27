"""
Django admin configuration for DataStream model.
"""

from django.contrib import admin

from .models import DataStream


@admin.register(DataStream)
class DataStreamAdmin(admin.ModelAdmin):
    model = DataStream
    list_display = (
        "id",
        "user",
        "source_type",
        "status",
        "created_at",
        "processed_at",
    )
    list_filter = ("source_type", "status", "created_at")
    search_fields = ("user__email", "source_type")
    readonly_fields = ("created_at", "updated_at", "processed_at")
    ordering = ("-created_at",)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if not request.user.is_superuser:
            queryset = queryset.filter(user=request.user)
        return queryset

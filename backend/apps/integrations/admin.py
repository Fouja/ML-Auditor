from django.contrib import admin

from .models import IntegrationConnection, SyncLog


@admin.register(IntegrationConnection)
class IntegrationConnectionAdmin(admin.ModelAdmin):
    list_display = ("user", "service", "status", "last_synced", "items_synced", "updated_at")
    list_filter = ("service", "status")
    search_fields = ("user__email",)


@admin.register(SyncLog)
class SyncLogAdmin(admin.ModelAdmin):
    list_display = ("connection", "started_at", "finished_at", "success", "items_synced")
    list_filter = ("success",)

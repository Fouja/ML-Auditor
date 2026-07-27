"""
Django admin configuration for DocumentChunk model.
"""

from django.contrib import admin

from .models import DocumentChunk


@admin.register(DocumentChunk)
class DocumentChunkAdmin(admin.ModelAdmin):
    model = DocumentChunk
    list_display = (
        "id",
        "stream",
        "cluster_category",
        "chunk_index",
        "total_chunks",
        "created_at",
    )
    list_filter = ("cluster_category", "created_at")
    search_fields = ("content",)
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-created_at",)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if not request.user.is_superuser:
            queryset = queryset.filter(stream__user=request.user)
        return queryset

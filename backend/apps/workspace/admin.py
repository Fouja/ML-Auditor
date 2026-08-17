"""
Admin configuration for Workspace models.
"""

from django.contrib import admin

from .models import (
    CalendarEvent,
    GeneratedDocument,
    NewsArticle,
    NewsFeed,
    Note,
    Task,
    Trigger,
    WorkspaceWidget,
)


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ["title", "status", "priority", "due_date", "created_at"]
    list_filter = ["status", "priority"]
    search_fields = ["title", "description"]


@admin.register(CalendarEvent)
class CalendarEventAdmin(admin.ModelAdmin):
    list_display = ["title", "start_time", "end_time", "location"]
    list_filter = ["all_day", "recurrence"]
    search_fields = ["title", "description"]


@admin.register(NewsFeed)
class NewsFeedAdmin(admin.ModelAdmin):
    list_display = ["name", "url", "feed_type", "is_active", "last_scraped"]
    list_filter = ["feed_type", "is_active"]


@admin.register(NewsArticle)
class NewsArticleAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "feed",
        "author",
        "published_at",
        "is_read",
        "is_bookmarked",
    ]
    list_filter = ["is_read", "is_bookmarked"]
    search_fields = ["title", "content"]


@admin.register(WorkspaceWidget)
class WorkspaceWidgetAdmin(admin.ModelAdmin):
    list_display = ["title", "widget_type", "position_x", "position_y", "is_visible"]
    list_filter = ["widget_type", "is_visible"]


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ["title", "format", "is_pinned", "updated_at", "created_at"]
    list_filter = ["format", "is_pinned"]
    search_fields = ["title", "content"]


@admin.register(Trigger)
class TriggerAdmin(admin.ModelAdmin):
    list_display = ["name", "trigger_type", "trigger_time", "is_active", "last_fired"]
    list_filter = ["trigger_type", "is_active"]


@admin.register(GeneratedDocument)
class GeneratedDocumentAdmin(admin.ModelAdmin):
    list_display = ["title", "doc_format", "file_format", "style", "updated_at"]
    list_filter = ["doc_format", "file_format"]
    search_fields = ["title", "content"]

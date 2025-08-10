from django.contrib import admin
from .models import Task
# Register your models here.


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "user", "completed", "created_at")
    list_filter = ("completed", "created_at", "user")
    search_fields = ("title", "description", "user__username", "user__email")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    readonly_fields = ("created_at",)
    autocomplete_fields = ("user",)

    actions = ["mark_completed", "mark_uncompleted"]

    def mark_completed(self, request, queryset):
        updated = queryset.update(completed=True)
        self.message_user(request, f"{updated} tasks marked as completed.")
    mark_completed.short_description = "Mark selected tasks as completed"

    def mark_uncompleted(self, request, queryset):
        updated = queryset.update(completed=False)
        self.message_user(request, f"{updated} tasks marked as uncompleted.")
    mark_uncompleted.short_description = "Mark selected tasks as uncompleted"

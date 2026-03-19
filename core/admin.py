from django.contrib import admin
from .models import (
    User,
    Category,
    Status,
    Complaint,
    Comment,
    ComplaintStatusHistory,
    Notification,
    AuditLog,
)


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("username", "email", "role", "is_staff", "is_active")
    search_fields = ("username", "email")
    list_filter = ("role", "is_active")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(Status)
class StatusAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "order")
    search_fields = ("name", "slug")
    ordering = ("order",)


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "status", "priority", "assigned_to", "created_at")
    list_filter = ("status", "priority", "category")
    search_fields = ("title", "description", "user__username")
    ordering = ("-created_at",)


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("complaint", "user", "is_internal", "created_at")
    list_filter = ("is_internal",)


@admin.register(ComplaintStatusHistory)
class ComplaintStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ("complaint", "old_status", "new_status", "changed_by", "created_at")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "message", "is_read", "created_at")
    list_filter = ("is_read",)
    search_fields = ("user__username", "message")


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("actor", "action", "entity", "entity_id", "created_at")
    list_filter = ("action", "entity")
    search_fields = ("actor__username", "entity", "detail")

from django.contrib import admin
from .models import Category, Priority, Status, Ticket, Comment, TicketHistory


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'created_at']
    search_fields = ['name']


@admin.register(Priority)
class PriorityAdmin(admin.ModelAdmin):
    list_display = ['name', 'level', 'color']
    list_filter = ['level']


@admin.register(Status)
class StatusAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_closed']
    list_filter = ['is_closed']


class CommentInline(admin.TabularInline):
    model = Comment
    extra = 0
    readonly_fields = ['user', 'created_at']


class TicketHistoryInline(admin.TabularInline):
    model = TicketHistory
    extra = 0
    readonly_fields = ['user', 'field_name', 'old_value', 'new_value', 'created_at']


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ['ticket_number', 'title', 'category', 'priority', 'status', 'assigned_to', 'created_at']
    list_filter = ['status', 'priority', 'category', 'created_at']
    search_fields = ['ticket_number', 'title', 'description']
    readonly_fields = ['ticket_number', 'created_by', 'created_at', 'updated_at']
    inlines = [CommentInline, TicketHistoryInline]
    
    def save_model(self, request, obj, form, change):
        if not change:  #si es un nuevo ticket
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['ticket', 'user', 'content_preview', 'is_internal', 'created_at']
    list_filter = ['is_internal', 'created_at']
    search_fields = ['content', 'ticket__ticket_number']
    readonly_fields = ['user', 'created_at', 'updated_at']
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content'


@admin.register(TicketHistory)
class TicketHistoryAdmin(admin.ModelAdmin):
    list_display = ['ticket', 'user', 'field_name', 'created_at']
    list_filter = ['field_name', 'created_at']
    search_fields = ['ticket__ticket_number']
    readonly_fields = ['ticket', 'user', 'field_name', 'old_value', 'new_value', 'created_at']
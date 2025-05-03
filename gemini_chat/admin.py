from django.contrib import admin
from .models import GeminiChatSession, GeminiChatMessage

class GeminiChatMessageInline(admin.TabularInline):
    model = GeminiChatMessage
    readonly_fields = ['role', 'content', 'created_at']
    extra = 0
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False
        
@admin.register(GeminiChatSession)
class GeminiChatSessionAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'title', 'session_id', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['title', 'user__username', 'user__email', 'session_id']
    readonly_fields = ['session_id', 'created_at', 'updated_at']
    inlines = [GeminiChatMessageInline]
    
    fieldsets = (
        ('Thông tin phiên', {
            'fields': ('user', 'title', 'session_id', 'is_active')
        }),
        ('Thời gian', {
            'fields': ('created_at', 'updated_at')
        }),
    )

@admin.register(GeminiChatMessage)
class GeminiChatMessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'session', 'role', 'short_content', 'created_at']
    list_filter = ['role', 'created_at']
    search_fields = ['content', 'session__title', 'session__user__username']
    readonly_fields = ['created_at']
    
    def short_content(self, obj):
        if len(obj.content) > 100:
            return obj.content[:97] + '...'
        return obj.content
    short_content.short_description = 'Nội dung'

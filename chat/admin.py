from django.contrib import admin
from .models import Message
from django.contrib import admin
from django.contrib.postgres.fields import ArrayField
from django.db import models
from unfold.admin import ModelAdmin
from unfold.contrib.forms.widgets import ArrayWidget, WysiwygWidget
from base.admin import BaseAdminClass

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'sender', 'recipient', 'content', 'created_at', 'is_read')
    list_display_links = ('id', 'content')
    list_filter = ('is_read', 'created_at')
    search_fields = ('content', 'sender__username', 'recipient__username')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)
    
    def sender(self, obj):
        return obj.sender.username if obj.sender else '-'
    sender.short_description = 'Người gửi'
    
    def recipient(self, obj):
        return obj.recipient.username if obj.recipient else '-'
    recipient.short_description = 'Người nhận'


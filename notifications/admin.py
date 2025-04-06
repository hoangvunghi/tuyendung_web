from django.contrib import admin
from .models import Notification
from django.contrib import admin
from django.contrib.postgres.fields import ArrayField
from django.db import models
from unfold.admin import ModelAdmin
from unfold.contrib.forms.widgets import ArrayWidget, WysiwygWidget
from base.admin import BaseAdminClass

@admin.register(Notification)
class NotificationAdmin(BaseAdminClass):
    list_display = ('recipient', 'notification_type', 'title', 'message', 'is_read', 'created_at')
    list_filter = ('recipient', 'notification_type', 'title', 'message', 'is_read', 'created_at')
    search_fields = ('recipient', 'notification_type', 'title', 'message', 'created_at')
    list_editable = ('is_read',)
    list_display_links = ('recipient', 'notification_type', 'title', 'message', 'created_at')



from django.contrib import admin
from .models import Interview
from django.contrib import admin
from django.contrib.postgres.fields import ArrayField
from django.db import models
from unfold.admin import ModelAdmin
from unfold.contrib.forms.widgets import ArrayWidget, WysiwygWidget
from base.admin import BaseAdminClass

@admin.register(Interview)
class InterviewAdmin(BaseAdminClass):
    list_display = ('enterprise', 'candidate', 'cv', 'title', 'description', 'interview_date', 'location', 'status', 'note', 'created_at', 'updated_at')
    list_filter = ('enterprise', 'candidate', 'cv', 'title', 'description', 'interview_date', 'location', 'status', 'note', 'created_at', 'updated_at')
    search_fields = ('enterprise', 'candidate', 'cv', 'title', 'description', 'interview_date', 'location', 'status', 'note', 'created_at', 'updated_at')
    list_display_links = ('enterprise', 'candidate', 'cv', 'title', 'description', 'interview_date', 'location', 'status', 'note', 'created_at', 'updated_at')  
    
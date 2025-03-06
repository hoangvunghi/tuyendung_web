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
    pass

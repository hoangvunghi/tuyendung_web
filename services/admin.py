from django.contrib import admin
from .models import *
# Register your models here.


from django.contrib import admin
from django.contrib.postgres.fields import ArrayField
from django.db import models
from unfold.admin import ModelAdmin
from unfold.contrib.forms.widgets import ArrayWidget, WysiwygWidget
from base.admin import BaseAdminClass

@admin.register(TypeService)
class TypeServiceAdmin(BaseAdminClass):
    list_display = ('name', 'status', 'description', 'created_at', 'modified_at')
    list_filter = ('name', 'status', 'description', 'created_at', 'modified_at')
    search_fields = ('name', 'status', 'description', 'created_at', 'modified_at')
    list_display_links = ('name', 'status', 'description', 'created_at', 'modified_at')

@admin.register(PackageEntity)
class PackageEntityAdmin(BaseAdminClass):
    list_display = ('name', 'status', 'description', 'price', 'type_service', 'days', 'created_at', 'modified_at')
    list_filter = ('name', 'status', 'description', 'price', 'type_service', 'days', 'created_at', 'modified_at')
    search_fields = ('name', 'status', 'description', 'price', 'type_service', 'days', 'created_at', 'modified_at')
    list_display_links = ('name', 'status', 'description', 'price', 'type_service', 'days', 'created_at', 'modified_at')

@admin.register(PackageCampaign)
class PackageCampaignAdmin(BaseAdminClass):
    list_display = ('package', 'campaign', 'expired', 'created_at', 'modified_at')
    list_filter = ('package', 'campaign', 'expired', 'created_at', 'modified_at')
    search_fields = ('package', 'campaign', 'expired', 'created_at', 'modified_at')
    list_display_links = ('package', 'campaign', 'expired', 'created_at', 'modified_at')

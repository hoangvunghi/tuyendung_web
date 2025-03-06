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
    pass

@admin.register(PackageEntity)
class PackageEntityAdmin(BaseAdminClass):
    pass

@admin.register(PackageCampaign)
class PackageCampaignAdmin(BaseAdminClass):
    pass
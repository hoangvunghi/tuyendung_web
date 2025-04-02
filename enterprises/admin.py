from django.contrib import admin
from .models import *
# Register your models here.

# admin.site.register(EnterpriseEntity)
# admin.site.register(FieldEntity)
# admin.site.register(CampaignEntity)
# admin.site.register(PositionEntity)
# admin.site.register(PostEntity)
# admin.site.register(CriteriaEntity)

from django.contrib import admin
from django.contrib.postgres.fields import ArrayField
from django.db import models
from unfold.admin import ModelAdmin
from unfold.contrib.forms.widgets import ArrayWidget, WysiwygWidget
from base.admin import BaseAdminClass

@admin.register(EnterpriseEntity)
class EnterpriseAdmin(BaseAdminClass):
    pass

@admin.register(FieldEntity)
class FieldAdmin(BaseAdminClass):
    pass

# @admin.register(CampaignEntity)
# class CampaignAdmin(BaseAdminClass):
#     pass

@admin.register(PositionEntity)
class PositionAdmin(BaseAdminClass):
    pass

@admin.register(PostEntity)
class PostAdmin(BaseAdminClass):
    pass

@admin.register(CriteriaEntity)
class CriteriaAdmin(BaseAdminClass):
    pass


# admin.site.register(EnterpriseEntity)
# admin.site.register(FieldEntity)
# admin.site.register(CampaignEntity)
# admin.site.register(PositionEntity)
# admin.site.register(PostEntity)
# admin.site.register(CriteriaEntity)

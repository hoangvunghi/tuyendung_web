from django.contrib import admin
from .models import UserAccount,UserRole,Role
from django.contrib import admin
from django.contrib.postgres.fields import ArrayField
from django.db import models
from unfold.admin import ModelAdmin
from unfold.contrib.forms.widgets import ArrayWidget, WysiwygWidget
from base.admin import BaseAdminClass

@admin.register(UserAccount)
class UserAccountAdmin(BaseAdminClass):
    pass

@admin.register(UserRole)
class UserRoleAdmin(BaseAdminClass):
    pass

@admin.register(Role)
class RoleAdmin(BaseAdminClass):
    pass

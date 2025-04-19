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
    list_display = ('username', 'email', 'is_active', 'is_staff', 'is_banned','is_premium','premium_expiry')
    list_filter = ('is_active', 'is_staff', 'is_banned')
    search_fields = ('username',)
    list_per_page = 10
    list_max_show_all = 100
    list_editable = ('is_active', 'is_staff', 'is_banned','is_premium','premium_expiry')
    list_display_links = ('username',)

    compressed_fields = True  
    warn_unsaved_form = True 
    list_filter_submit = True 
    change_form_show_cancel_button = True 
    formfield_overrides = {
        models.TextField: {
            "widget": WysiwygWidget,
        },
        ArrayField: {
            "widget": ArrayWidget,
        },
    }

@admin.register(UserRole)
class UserRoleAdmin(BaseAdminClass):
    list_display = ('username', 'rolename')
    list_filter = ('user__email', 'role__name')  
    search_fields = ('user__email', 'role__name')
    list_per_page = 10
    list_max_show_all = 100
    list_display_links = ('username', 'rolename')

    def username(self, obj):
        return obj.user.username
    username.short_description = 'Tài khoản'

    def rolename(self, obj):
        return obj.role.name
    rolename.short_description = 'Vai trò'

@admin.register(Role)
class RoleAdmin(BaseAdminClass):
    list_display = ('name',)
    list_filter = ('name',)
    search_fields = ('name',)
    list_per_page = 10
    list_max_show_all = 100
    list_display_links = ('name',)

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.models import User, Group

from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm
from unfold.admin import ModelAdmin
from unfold.contrib.forms.widgets import ArrayWidget, WysiwygWidget
from django.contrib.postgres.fields import ArrayField
from django.db import models

admin.site.unregister(Group)

@admin.register(Group)
class GroupAdmin(BaseGroupAdmin, ModelAdmin):
    pass


class BaseAdminClass(ModelAdmin):
    compressed_fields = True  
    warn_unsaved_form = True  
    readonly_preprocess_fields = {
        "model_field_name": "html.unescape",
        "other_field_name": lambda content: content.strip(),
    }
    list_filter_submit = False
    list_fullwidth = False
    list_filter_sheet = True
    list_horizontal_scrollbar_top = False
    list_disable_select_all = False
    # Custom actions
    actions_list = []  
    actions_row = []  
    actions_detail = []  
    actions_submit_line = []  
    change_form_show_cancel_button = True

    formfield_overrides = {
        models.TextField: {
            "widget": WysiwygWidget,
        },
        ArrayField: {
            "widget": ArrayWidget,
        }
    }
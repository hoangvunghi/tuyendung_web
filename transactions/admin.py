from django.contrib import admin
from .models import *
# Register your models here.
from django.contrib import admin
from django.contrib.postgres.fields import ArrayField
from django.db import models
from unfold.admin import ModelAdmin
from unfold.contrib.forms.widgets import ArrayWidget, WysiwygWidget
from base.admin import BaseAdminClass

@admin.register(HistoryMoney)
class HistoryMoneyAdmin(BaseAdminClass):
    list_display = ('user', 'amount', 'balance_after', 'is_add_money', 'created_at', 'modified_at')
    list_filter = ('user', 'amount', 'balance_after', 'is_add_money', 'created_at', 'modified_at')
    search_fields = ('user', 'amount', 'balance_after', 'is_add_money', 'created_at', 'modified_at')
    list_display_links = ('user', 'amount', 'balance_after', 'is_add_money', 'created_at', 'modified_at')

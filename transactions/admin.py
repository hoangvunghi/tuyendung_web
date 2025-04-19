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

@admin.register(VnPayTransaction)
class VnPayTransactionAdmin(BaseAdminClass):
    list_display = ('user', 'amount', 'transaction_status', 'txn_ref', 'created_at')
    list_filter = ('transaction_status', 'created_at')
    search_fields = ('user__username', 'user__email', 'txn_ref', 'transaction_no')
    readonly_fields = ('created_at', 'modified_at', 'transaction_no', 'transaction_status', 'txn_ref')
    ordering = ('-created_at',)
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user')
    
    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(PremiumPackage)
class PremiumPackageAdmin(BaseAdminClass):
    list_display = ('name', 'price', 'duration_days', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)

    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(PremiumHistory)
class PremiumHistoryAdmin(BaseAdminClass):
    list_display = ('user', 'package', 'start_date', 'end_date', 'is_active', 'is_cancelled')
    list_filter = ('is_active', 'is_cancelled')

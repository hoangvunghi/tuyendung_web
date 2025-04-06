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
    list_display = ('company_name', 'address', 'phone_number', 'email_company', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('company_name', 'address', 'phone_number', 'email_company')
    list_per_page = 10
    list_max_show_all = 100
    list_editable = ('is_active',)
    list_display_links = ('company_name', 'address')

    def company_name(self, obj):
        return obj.company_name
    company_name.short_description = 'Tên doanh nghiệp'

    def address(self, obj):
        return obj.address
    address.short_description = 'Địa chỉ'

    def phone_number(self, obj):
        return obj.phone_number
    phone_number.short_description = 'Số điện thoại'
    

@admin.register(FieldEntity)
class FieldAdmin(BaseAdminClass):
    list_display = ('name', 'code', 'status')
    list_filter = ('status',)
    search_fields = ('name', 'code')
    list_per_page = 10
    list_max_show_all = 100
    list_editable = ('status',)
    list_display_links = ('name', 'code')


@admin.register(PositionEntity)
class PositionAdmin(BaseAdminClass):
    list_display = ('name', 'code', 'field', 'status')
    list_filter = ('status', 'field')
    search_fields = ('name', 'code')
    list_per_page = 10
    list_max_show_all = 100
    list_editable = ('status',)
    list_display_links = ('name', 'code')

@admin.register(PostEntity)
class PostAdmin(BaseAdminClass):
    list_display = ('title', 'deadline', 'enterprise', 'position', 'field', 'is_active')
    list_filter = ('is_active', 'enterprise', 'position', 'field')
    search_fields = ('title', 'deadline', 'enterprise__company_name', 'position__name', 'field__name')
    list_per_page = 10
    list_max_show_all = 100
    list_editable = ('is_active',)
    list_display_links = ('title', 'deadline')

    

@admin.register(CriteriaEntity)
class CriteriaAdmin(BaseAdminClass):
    list_display = ('city', 'experience', 'field', 'position', 'scales', 'type_working', 'user')
    list_filter = ('city', 'experience', 'field', 'position', 'scales', 'type_working', 'user')
    search_fields = ('city', 'experience', 'field', 'position', 'scales', 'type_working', 'user')
    list_per_page = 10
    list_max_show_all = 100
    list_display_links = ('city', 'experience') 






# # ----
# from django.db import models
# from accounts.models import UserAccount

# class EnterpriseEntity(models.Model):
#     company_name = models.CharField(max_length=255)
#     address = models.CharField(max_length=255)
#     business_certificate_url = models.CharField(max_length=255)
#     business_certificate_public_id = models.CharField(max_length=255)
#     description = models.TextField()
#     email_company = models.EmailField(max_length=255)
#     field_of_activity = models.TextField()
#     is_active = models.BooleanField(default=False)
#     link_web_site = models.URLField(max_length=255, blank=True)
#     logo_url = models.CharField(max_length=255, blank=True)
#     logo_public_id = models.CharField(max_length=255, blank=True)
#     background_image_url = models.CharField(max_length=255, blank=True)
#     background_image_public_id = models.CharField(max_length=255, blank=True)
#     phone_number = models.CharField(max_length=20)
#     scale = models.CharField(max_length=255)
#     tax = models.CharField(max_length=255)
#     user = models.ForeignKey(UserAccount, on_delete=models.CASCADE, related_name='enterprises')
#     city = models.CharField(max_length=255)
#     created_at = models.DateTimeField(auto_now_add=True)
#     modified_at = models.DateTimeField(auto_now=True)

#     class Meta:
#         verbose_name = 'Doanh nghiệp'
#         verbose_name_plural = 'Doanh nghiệp'

#     def __str__(self):
#         return self.company_name

# class FieldEntity(models.Model):
#     name = models.CharField(max_length=255)
#     code = models.CharField(max_length=255, unique=True)
#     STATUS_CHOICES = [
#         ('active', 'Active'),
#         ('inactive', 'Inactive')
#     ]
#     status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
#     created_at = models.DateTimeField(auto_now_add=True)
#     modified_at = models.DateTimeField(auto_now=True)
    
#     def __str__(self):
#         return self.name
    
#     class Meta:
#         verbose_name = 'Lĩnh vực'
#         verbose_name_plural = 'Lĩnh vực'


# class CampaignEntity(models.Model):
#     name = models.CharField(max_length=255)
#     is_active = models.BooleanField(default=False)
#     enterprise = models.ForeignKey(EnterpriseEntity, on_delete=models.CASCADE, related_name='campaigns')
#     created_at = models.DateTimeField(auto_now_add=True)
#     modified_at = models.DateTimeField(auto_now=True)
    
#     def __str__(self):
#         return self.name
    
#     class Meta:
#         verbose_name = 'Chiến dịch'
#         verbose_name_plural = 'Chiến dịch'


# class PositionEntity(models.Model):
#     name = models.CharField(max_length=255)
#     code = models.CharField(max_length=255, unique=True)
#     field = models.ForeignKey(FieldEntity, on_delete=models.CASCADE, related_name='positions')
#     STATUS_CHOICES = [
#         ('active', 'Active'),
#         ('inactive', 'Inactive')
#     ]
#     status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
#     created_at = models.DateTimeField(auto_now_add=True)
#     modified_at = models.DateTimeField(auto_now=True)
    
#     def __str__(self):
#         return self.name
    
#     class Meta:
#         verbose_name = 'Vị trí'
#         verbose_name_plural = 'Vị trí'

# class PostEntity(models.Model):
#     title = models.CharField(max_length=255, db_index=True)
#     deadline = models.DateField(null=True, blank=True)
#     district = models.CharField(max_length=100, default='', blank=True)
#     experience = models.CharField(max_length=50, db_index=True, default='Không yêu cầu')
#     enterprise = models.ForeignKey(EnterpriseEntity, on_delete=models.CASCADE, related_name='posts')
#     position = models.ForeignKey(PositionEntity, on_delete=models.CASCADE, related_name='posts')
#     field = models.ForeignKey(FieldEntity, on_delete=models.SET_NULL, null=True, blank=True, related_name='posts')
#     interest = models.TextField(default='')
#     level = models.CharField(max_length=50, default='', blank=True)
#     quantity = models.IntegerField(default=1)
#     required = models.TextField(default='')
#     salary_min = models.IntegerField(default=0)
#     salary_max = models.IntegerField(default=0)
#     is_salary_negotiable = models.BooleanField(default=False, db_index=True)
#     time_working = models.CharField(max_length=255, default='', blank=True)
#     type_working = models.CharField(max_length=50, db_index=True, default='Toàn thời gian')
#     city = models.CharField(max_length=100, db_index=True)
#     description = models.TextField(default='')
#     detail_address = models.CharField(max_length=255, default='', blank=True)
#     created_at = models.DateTimeField(auto_now_add=True, db_index=True)
#     modified_at = models.DateTimeField(auto_now=True)
#     is_active = models.BooleanField(default=False, db_index=True)
    
#     def __str__(self):
#         return self.title

#     class Meta:
#         db_table = 'posts'
#         ordering = ['-created_at']
#         indexes = [
#             models.Index(fields=['title', 'city', 'experience', 'type_working']),
#             models.Index(fields=['is_active', 'is_salary_negotiable']),
#             models.Index(fields=['salary_min', 'salary_max']),
#         ]

# class CriteriaEntity(models.Model):
#     city = models.CharField(max_length=255)
#     experience = models.CharField(max_length=255)
#     field = models.ForeignKey(FieldEntity, on_delete=models.CASCADE, related_name='criteria')
#     position = models.ForeignKey(PositionEntity, on_delete=models.CASCADE, related_name='criteria')
#     scales = models.CharField(max_length=255)
#     type_working = models.CharField(max_length=255)
#     user = models.ForeignKey(UserAccount, on_delete=models.CASCADE, related_name='criteria')
#     created_at = models.DateTimeField(auto_now_add=True)
#     modified_at = models.DateTimeField(auto_now=True)
    
#     def __str__(self):
#         return f"Criteria for {self.user.username}"
    
#     class Meta:
#         verbose_name = 'Tiêu chí'
#         verbose_name_plural = 'Tiêu chí'
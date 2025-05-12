from django.contrib import admin
from .models import *
from notifications.models import Notification

from django.contrib import admin
from django.contrib.postgres.fields import ArrayField
from django.db import models
from unfold.admin import ModelAdmin
from unfold.contrib.forms.widgets import ArrayWidget, WysiwygWidget
from base.admin import BaseAdminClass
from django.utils.html import format_html

@admin.register(EnterpriseEntity)
class EnterpriseAdmin(BaseAdminClass):
    list_display = ('company_name', 'address', 'phone_number', 'email_company', 'is_active', 'show_certificate')
    list_filter = ('is_active',)
    search_fields = ('company_name', 'address', 'phone_number', 'email_company')
    list_per_page = 10
    list_max_show_all = 100
    list_editable = ('is_active',)
    list_display_links = ('company_name', 'address')
    compressed_fields = True  # Hiển thị form chỉnh sửa ở chế độ thu gọn
    warn_unsaved_form = True  # Cảnh báo khi có thay đổi chưa lưu
    list_filter_submit = True  # Thêm nút submit trong bộ lọc
    change_form_show_cancel_button = True  # Hiển thị nút Cancel trong form

    # Tùy chỉnh widget cho các trường
    formfield_overrides = {
        models.TextField: {
            "widget": WysiwygWidget,
        },
    }

    def company_name(self, obj):
        return obj.company_name
    company_name.short_description = 'Tên doanh nghiệp'

    def address(self, obj):
        return obj.address
    address.short_description = 'Địa chỉ'

    def phone_number(self, obj):
        return obj.phone_number
    phone_number.short_description = 'Số điện thoại'
    
    def show_certificate(self, obj):
        if obj.business_certificate_url:
            if obj.business_certificate_url.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                return format_html(
                    '<a href="{0}" target="_blank"><img src="{0}" style="max-width:120px;max-height:80px;" /></a>',
                    obj.business_certificate_url
                )
            else:
                return format_html('<a href="{0}" target="_blank">Xem file</a>', obj.business_certificate_url)
        return "Chưa có"
    show_certificate.short_description = "Chứng nhận KD"

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

@admin.register(SavedPostEntity)
class SavedPostEntityAdmin(BaseAdminClass):
    list_display = ('user', 'post', 'created_at')
    list_filter = ('user', 'post')
    search_fields = ('user__username', 'post__title')
    list_per_page = 10
    list_max_show_all = 100
    list_display_links = ('user', 'post')

@admin.register(ReportPostEntity)
class ReportPostEntityAdmin(ModelAdmin):
    list_display = ('user', 'post', 'created_at', 'status', 'is_remove')
    list_filter = ('status', 'is_remove')
    search_fields = ('user__username', 'post__title', 'reason')
    readonly_fields = ('created_at', 'modified_at')
    fields = ('user', 'post', 'reason', 'response', 'status', 'is_remove')
    
    def save_model(self, request, obj, form, change):
        # Nếu is_remove được đánh dấu, cập nhật trạng thái bài đăng
        if obj.status:
            remove = False
            if obj.is_remove:
                remove = True
                post = obj.post
                post.is_active = False
                post.is_remove_by_admin = True
                post.save()
            # tạo notification
            from django.contrib.contenttypes.models import ContentType
            report_content_type = ContentType.objects.get_for_model(ReportPostEntity)
            
            if remove:
                Notification.objects.create(
                    recipient=obj.user,
                    notification_type='report_post',
                    title=f'Báo cáo bài đăng {obj.post.title}',
                    message=f'Bài đăng {obj.post.title} do bạn báo cáo đã bị gỡ',
                    content_type=report_content_type,
                    object_id=obj.id,
                )
                # tạo notification cho doanh nghiệp
                Notification.objects.create(
                    recipient=obj.post.enterprise.user,
                    notification_type='report_post',
                    title=f'Báo cáo bài đăng {obj.post.title}',
                    message=f'Bài đăng {obj.post.title} do bạn báo cáo đã bị gỡ với lí do: {obj.response}',
                    content_type=report_content_type,
                    object_id=obj.id,
                )
            else:
                Notification.objects.create(
                    recipient=obj.user,
                    notification_type='report_post',
                    title=f'Báo cáo bài đăng {obj.post.title}',
                    message=f'Bài đăng {obj.post.title} do bạn báo cáo không vi phạm',
                    content_type=report_content_type,
                    object_id=obj.id,
                )

        super().save_model(request, obj, form, change)
    
    # Bỏ comment để cho phép thêm báo cáo từ admin
    # def has_add_permission(self, request):
    #     # Không cho phép thêm báo cáo từ admin
    #     return False

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
from django.db import models
from accounts.models import UserAccount
import re
def strip_html_tags(text):
    if text:
        clean = re.compile('<.*?>')
        return re.sub(clean, '', text)
    return text
class EnterpriseEntity(models.Model):
    company_name = models.CharField(max_length=255, db_index=True)
    address = models.CharField(max_length=255)
    business_certificate_url = models.CharField(max_length=255,blank=True,null=True)
    business_certificate_public_id = models.CharField(max_length=255,blank=True,null=True)
    description = models.TextField()
    email_company = models.EmailField(max_length=255)
    field_of_activity = models.TextField(db_index=True)
    is_active = models.BooleanField(default=False, db_index=True)
    link_web_site = models.URLField(max_length=255, blank=True,null=True)
    logo_url = models.CharField(max_length=255, blank=True,null=True)
    logo_public_id = models.CharField(max_length=255, blank=True,null=True)
    background_image_url = models.CharField(max_length=255, blank=True,null=True)
    background_image_public_id = models.CharField(max_length=255, blank=True)
    phone_number = models.CharField(max_length=20)
    scale = models.CharField(max_length=255, db_index=True)
    tax = models.CharField(max_length=255)
    user = models.ForeignKey(UserAccount, on_delete=models.CASCADE, related_name='enterprises')
    city = models.CharField(max_length=255, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Doanh nghiệp'
        verbose_name_plural = 'Doanh nghiệp'
        indexes = [
            models.Index(fields=['company_name', 'city'], name='company_city_idx'),
            models.Index(fields=['company_name', 'field_of_activity'], name='company_field_idx'),
            models.Index(fields=['is_active', 'scale'], name='active_scale_idx'),
            models.Index(fields=['created_at'], name='enterprise_created_idx'),
        ]

    def __str__(self):
        return self.company_name
    
    def save(self, *args, **kwargs):
        self.description = strip_html_tags(self.description)
        self.field_of_activity = strip_html_tags(self.field_of_activity)
        super().save(*args, **kwargs)

class FieldEntity(models.Model):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=255, unique=True)
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive')
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = 'Lĩnh vực'
        verbose_name_plural = 'Lĩnh vực'


class CampaignEntity(models.Model):
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=False)
    enterprise = models.ForeignKey(EnterpriseEntity, on_delete=models.CASCADE, related_name='campaigns')
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = 'Chiến dịch'
        verbose_name_plural = 'Chiến dịch'


class PositionEntity(models.Model):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=255, unique=True)
    field = models.ForeignKey(FieldEntity, on_delete=models.CASCADE, related_name='positions')
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive')
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        self.name = strip_html_tags(self.name)
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Vị trí'
        verbose_name_plural = 'Vị trí'

class PostEntity(models.Model):
    title = models.CharField(max_length=255, db_index=True)
    deadline = models.DateField(null=True, blank=True)
    district = models.CharField(max_length=100, default='', blank=True)
    experience = models.CharField(max_length=50, db_index=True, default='Không yêu cầu')
    enterprise = models.ForeignKey(EnterpriseEntity, on_delete=models.CASCADE, related_name='posts')
    position = models.ForeignKey(PositionEntity, on_delete=models.CASCADE, related_name='posts')
    field = models.ForeignKey(FieldEntity, on_delete=models.SET_NULL, null=True, blank=True, related_name='posts')
    interest = models.TextField(default='')
    level = models.CharField(max_length=50, default='', blank=True)
    quantity = models.IntegerField(default=1)
    required = models.TextField(default='')
    salary_min = models.IntegerField(default=0)
    salary_max = models.IntegerField(default=0)
    is_salary_negotiable = models.BooleanField(default=False, db_index=True)
    time_working = models.CharField(max_length=255, default='', blank=True)
    type_working = models.CharField(max_length=50, db_index=True, default='Toàn thời gian')
    city = models.CharField(max_length=100, db_index=True)
    description = models.TextField(default='')
    detail_address = models.CharField(max_length=255, default='', blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    modified_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=False, db_index=True)
    
    def __str__(self):
        return self.title

    class Meta:
        db_table = 'posts'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['title', 'city', 'experience', 'type_working']),
            models.Index(fields=['is_active', 'is_salary_negotiable']),
            models.Index(fields=['salary_min', 'salary_max']),
        ]

class CriteriaEntity(models.Model):
    city = models.CharField(max_length=255)
    experience = models.CharField(max_length=255)
    field = models.ForeignKey(FieldEntity, on_delete=models.CASCADE, related_name='criteria')
    position = models.ForeignKey(PositionEntity, on_delete=models.CASCADE, related_name='criteria')
    scales = models.CharField(max_length=255)
    type_working = models.CharField(max_length=255)
    user = models.ForeignKey(UserAccount, on_delete=models.CASCADE, related_name='criteria')
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Criteria for {self.user.username}"
    
    class Meta:
        verbose_name = 'Tiêu chí'
        verbose_name_plural = 'Tiêu chí'
from django.db import models
from accounts.models import UserAccount

class EnterpriseEntity(models.Model):
    company_name = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    business_certificate_url = models.CharField(max_length=255)
    business_certificate_public_id = models.CharField(max_length=255)
    description = models.TextField()
    email_company = models.EmailField(max_length=255)
    field_of_activity = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    link_web_site = models.URLField(max_length=255, blank=True)
    logo_url = models.CharField(max_length=255, blank=True)
    logo_public_id = models.CharField(max_length=255, blank=True)
    background_image_url = models.CharField(max_length=255, blank=True)
    background_image_public_id = models.CharField(max_length=255, blank=True)
    phone_number = models.CharField(max_length=20)
    scale = models.CharField(max_length=255)
    tax = models.CharField(max_length=255)
    user = models.ForeignKey(UserAccount, on_delete=models.CASCADE, related_name='enterprises')
    city = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Doanh nghiệp'
        verbose_name_plural = 'Doanh nghiệp'

    def __str__(self):
        return self.company_name

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
    is_active = models.BooleanField(default=True)
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
        verbose_name = 'Vị trí'
        verbose_name_plural = 'Vị trí'

class PostEntity(models.Model):
    title = models.CharField(max_length=255)
    deadline = models.DateField()
    district = models.CharField(max_length=255)
    experience = models.CharField(max_length=255)
    # campaign = models.ForeignKey(CampaignEntity, on_delete=models.CASCADE, related_name='posts')
    enterprise = models.ForeignKey(EnterpriseEntity, on_delete=models.CASCADE, related_name='posts')
    position = models.ForeignKey(PositionEntity, on_delete=models.CASCADE, related_name='posts')
    interest = models.TextField()
    level = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField()
    required = models.TextField()
    salary_range = models.CharField(max_length=255)
    time_working = models.CharField(max_length=255)
    type_working = models.CharField(max_length=255)
    city = models.CharField(max_length=255)
    description = models.TextField()
    detail_address = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)  
    modified_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.title

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
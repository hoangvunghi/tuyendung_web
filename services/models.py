from django.db import models
from enterprises.models import CampaignEntity

class TypeService(models.Model):
    name = models.CharField(max_length=255)
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive')
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True) 
    
    def __str__(self):
        return self.name

class PackageEntity(models.Model):
    name = models.CharField(max_length=255)
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive')
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    type_service = models.ForeignKey(TypeService, on_delete=models.CASCADE, related_name='packages')
    days = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)  
    
    def __str__(self):
        return f"{self.name} ({self.days} days)"

class PackageCampaign(models.Model):
    package = models.ForeignKey(PackageEntity, on_delete=models.CASCADE, related_name='campaign_subscriptions')
    campaign = models.ForeignKey(CampaignEntity, on_delete=models.CASCADE, related_name='package_subscriptions')
    expired = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.campaign} - {self.package} (Expires: {self.expired})"
    
    class Meta:
        unique_together = ('package', 'campaign')
        verbose_name = 'Gói đăng ký'
        verbose_name_plural = 'Gói đăng ký'

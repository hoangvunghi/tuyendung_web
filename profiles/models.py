from django.db import models
from django.contrib.auth import get_user_model
from enterprises.models import PostEntity
from model_utils import FieldTracker

# Lấy model User từ settings
UserAccount = get_user_model()

class UserInfo(models.Model):
    user = models.OneToOneField(UserAccount, on_delete=models.CASCADE, related_name='profile')
    fullname = models.CharField(max_length=255)
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other')
    ]
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    balance = models.DecimalField(max_digits=38, decimal_places=2, default=0.00)
    cv_attachments_url = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)  
    
    def __str__(self):
        return self.fullname or self.user.username
    
    class Meta:
        verbose_name = 'Thông tin người dùng'
        verbose_name_plural = 'Thông tin người dùng'

class Cv(models.Model):
    user = models.ForeignKey(UserAccount, on_delete=models.CASCADE, related_name='cvs')
    post = models.ForeignKey(PostEntity, on_delete=models.CASCADE, related_name='cvs')
    name = models.CharField(max_length=255)
    email = models.EmailField(max_length=255)
    phone_number = models.CharField(max_length=20)
    description = models.TextField()  
    # cv_file = models.FileField(upload_to='cvs/', blank=True, null=True)
    cv_file_url = models.CharField(max_length=255, blank=True, null=True)
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    is_viewed = models.BooleanField(default=False)
    note = models.TextField(blank=True)  
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True) 
    tracker = FieldTracker(fields=['status'])
    
    def __str__(self):
        return f"CV: {self.name} for {self.post}"

    class Meta:
        verbose_name = 'CV'
        verbose_name_plural = 'CV'
        indexes = [
            models.Index(fields=['post', 'user'], name='cv_post_user_idx'),
            models.Index(fields=['post', 'status'], name='cv_post_status_idx'),
            models.Index(fields=['user', 'created_at'], name='cv_user_time_idx'),
            models.Index(fields=['post'], name='cv_post_idx'),
            models.Index(fields=['created_at'], name='cv_time_idx'),
        ]

# profiles/models.py
class CvView(models.Model):
    cv = models.ForeignKey('Cv', on_delete=models.CASCADE)
    viewer = models.ForeignKey('enterprises.EnterpriseEntity', on_delete=models.CASCADE)
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'CV đã xem'
        verbose_name_plural = 'CV đã xem'

class CvMark(models.Model):
    MARK_TYPES = (
        ('interested', 'Quan tâm'),
        ('shortlisted', 'Vào danh sách ngắn'),
        ('rejected', 'Từ chối'),
    )
    cv = models.ForeignKey('Cv', on_delete=models.CASCADE)
    marker = models.ForeignKey('enterprises.EnterpriseEntity', on_delete=models.CASCADE)
    mark_type = models.CharField(max_length=20, choices=MARK_TYPES)
    marked_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'CV đã đánh dấu'
        verbose_name_plural = 'CV đã đánh dấu'

# interviews/models.py
from django.db import models
from django.contrib.auth import get_user_model

class Interview(models.Model):
    INTERVIEW_STATUS = (
        ('pending', 'Chờ phản hồi'),
        ('accepted', 'Đã chấp nhận'),
        ('rejected', 'Đã từ chối'),
        ('completed', 'Đã hoàn thành'),
        ('cancelled', 'Đã hủy'),
    )

    enterprise = models.ForeignKey('enterprises.EnterpriseEntity', on_delete=models.CASCADE)
    candidate = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    cv = models.ForeignKey('profiles.Cv', on_delete=models.CASCADE)
    
    title = models.CharField(max_length=255)
    description = models.TextField()
    interview_date = models.DateTimeField()
    location = models.CharField(max_length=255)
    meeting_link = models.URLField(blank=True, null=True)  # Cho phỏng vấn online
    
    status = models.CharField(max_length=20, choices=INTERVIEW_STATUS, default='pending')
    note = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-interview_date']
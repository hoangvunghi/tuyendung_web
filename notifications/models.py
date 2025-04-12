from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('cv_viewed', 'CV được xem'),
        ('cv_status_changed', 'Trạng thái CV thay đổi'),
        ('cv_marked', 'CV được đánh dấu'),
        ('interview_invited', 'Mời phỏng vấn'),
        ('message_received', 'Tin nhắn mới'),
    )

    recipient = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    link = models.CharField(max_length=10000, default='')
    
    # Để lưu reference tới object gây ra notification (CV, Post, etc)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Thông báo'
        verbose_name_plural = 'Thông báo'
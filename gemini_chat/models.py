from django.db import models
from accounts.models import UserAccount

class GeminiChatSession(models.Model):
    """Model lưu trữ phiên chat với Gemini API"""
    user = models.ForeignKey(UserAccount, on_delete=models.CASCADE, related_name='gemini_chat_sessions')
    session_id = models.CharField(max_length=100, unique=True)
    title = models.CharField(max_length=255, default="Cuộc trò chuyện mới")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Chat session {self.session_id} - {self.user.username}"
    
    class Meta:
        verbose_name = 'Phiên chat Gemini'
        verbose_name_plural = 'Phiên chat Gemini'
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['user', 'created_at'], name='gemini_chat_user_time_idx'),
        ]

class GeminiChatMessage(models.Model):
    """Model lưu trữ tin nhắn trong phiên chat Gemini"""
    MESSAGE_ROLE_CHOICES = [
        ('user', 'User'),
        ('model', 'Gemini Model'),
        ('system', 'System'),
    ]
    
    session = models.ForeignKey(GeminiChatSession, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=10, choices=MESSAGE_ROLE_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.role}: {self.content[:50]}..."
    
    class Meta:
        verbose_name = 'Tin nhắn Gemini'
        verbose_name_plural = 'Tin nhắn Gemini'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['session', 'created_at'], name='gemini_msg_session_time_idx'),
        ]

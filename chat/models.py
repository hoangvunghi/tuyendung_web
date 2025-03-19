# chat/models.py
from django.db import models
from django.contrib.auth import get_user_model

class Message(models.Model):
    sender = models.ForeignKey(
        get_user_model(), 
        on_delete=models.CASCADE,
        related_name='sent_messages'
    )
    recipient = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name='received_messages'
    )
    content = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        # set name là tên của message
        verbose_name = 'Tin nhắn'
        verbose_name_plural = 'Tin nhắn'

    def __str__(self):
        return f'{self.sender} to {self.recipient} at {self.created_at}'

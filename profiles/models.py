from django.db import models
from accounts.models import UserAccount
from enterprises.models import PostEntity

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
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)  
    
    def __str__(self):
        return self.fullname or self.user.username

class Cv(models.Model):
    user = models.ForeignKey(UserAccount, on_delete=models.CASCADE, related_name='cvs')
    post = models.ForeignKey(PostEntity, on_delete=models.CASCADE, related_name='cvs')
    name = models.CharField(max_length=255)
    email = models.EmailField(max_length=255)
    phone_number = models.CharField(max_length=20)
    description = models.TextField()  
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    note = models.TextField(blank=True)  
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True) 
    
    def __str__(self):
        return f"CV: {self.name} for {self.post}"

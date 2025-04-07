from django.db import models
from django.contrib.auth.models import BaseUserManager
from django.contrib.auth.hashers import make_password, check_password
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
class UserAccountManager(BaseUserManager):
    def create_user(self, email, username, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, username=username, **extra_fields)
        user.password = make_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        return self.create_user(email, username, password, **extra_fields)

class UserAccount(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=255, unique=True)
    password = models.CharField(max_length=128)
    google_id = models.CharField(max_length=255, blank=True, null=True)
    is_active = models.BooleanField(default=False)
    is_banned = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    activation_token = models.CharField(max_length=255, blank=True, null=True)
    activation_token_expiry = models.DateTimeField(null=True, blank=True)  
    objects = UserAccountManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = [ 'email']

    def __str__(self):
        return self.email

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)

    def get_role(self):
        return self.user_roles.first().role.name
    
    def is_employer(self):
        return self.user_roles.filter(role__name='employer').exists()
    
    def get_enterprise(self):
        """
        Lấy doanh nghiệp của user nếu là employer, ngược lại trả về None
        """
        if self.is_employer():
            try:
                return self.enterprises.first()
            except:
                return None
        return None

    class Meta:
        verbose_name = 'Tài khoản'
        verbose_name_plural = 'Tài khoản'

    
class Role(models.Model):
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Vai trò'
        verbose_name_plural = 'Vai trò'

class UserRole(models.Model):
    user = models.ForeignKey(UserAccount, on_delete=models.CASCADE, related_name='user_roles')
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='user_roles')
    
    class Meta:
        unique_together = ('user', 'role')
        verbose_name = 'Vai trò người dùng'
        verbose_name_plural = 'Vai trò người dùng'
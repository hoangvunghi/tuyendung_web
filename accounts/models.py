from django.db import models
from django.contrib.auth.models import BaseUserManager
from django.contrib.auth.hashers import make_password, check_password
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.utils import timezone

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
    is_premium = models.BooleanField(default=False)
    premium_expiry = models.DateTimeField(null=True, blank=True)
    
    # Các thuộc tính theo dõi giới hạn premium
    post_count = models.IntegerField(default=0)  # Số bài đăng hiện tại
    cv_views_today = models.IntegerField(default=0)  # Số CV đã xem trong ngày
    last_cv_view_date = models.DateField(null=True, blank=True)  # Ngày cuối cùng xem CV
    job_applications_today = models.IntegerField(default=0)  # Số đơn ứng tuyển đã gửi trong ngày
    last_application_date = models.DateField(null=True, blank=True)  # Ngày cuối cùng gửi đơn ứng tuyển
    
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
        from enterprises.models import EnterpriseEntity
        if self.is_employer:
            try:
                return EnterpriseEntity.objects.get(user=self)
            except EnterpriseEntity.DoesNotExist:
                return None
        return None

    def get_full_name(self):
        # Lazy import để tránh circular import
        from profiles.models import UserInfo
        
        try:
            user_info = UserInfo.objects.filter(user=self).first()
            if user_info and user_info.fullname:
                return user_info.fullname
            return self.username  # Trả về username nếu không có fullname
        except Exception as e:
            # Xử lý ngoại lệ, trả về username
            return self.username

    def get_premium_package_name(self):
        """
        Lấy tên gói Premium hiện tại của người dùng từ lịch sử Premium
        """
        if not self.is_premium:
            return None
            
        try:
            # Import ở đây để tránh circular import
            from transactions.models import PremiumHistory
            
            # Lấy lịch sử Premium gần nhất và đang hoạt động
            premium_history = PremiumHistory.objects.filter(
                user=self,
                is_active=True,
                is_cancelled=False,
                end_date__gt=timezone.now()
            ).order_by('-created_at').first()
            
            if premium_history:
                return premium_history.package_name
                
            return "Premium"  # Mặc định nếu không tìm thấy
        except Exception as e:
            print(f"Error getting premium package name: {str(e)}")
            return "Premium"  # Mặc định nếu có lỗi
            
    def get_premium_package(self):
        """
        Lấy gói Premium hiện tại của người dùng
        """
        from transactions.models import PremiumHistory
        try:
            premium_history = PremiumHistory.objects.filter(
                user=self,
                is_active=True,
                expires_at__gt=timezone.now()
            ).select_related('premium_package').order_by('-expires_at').first()
            
            if premium_history:
                return premium_history.premium_package
            return None
        except:
            return None
    
    def can_post_job(self):
        """
        Kiểm tra xem người dùng có thể đăng thêm công việc không
        dựa trên giới hạn của gói Premium
        """
        # Admin có thể đăng bài không giới hạn
        if self.is_superuser:
            return True
            
        # Nếu không phải employer thì không được đăng bài
        if not self.is_employer:
            return False
            
        # Lấy gói Premium hiện tại
        premium_package = self.get_premium_package()
        
        # Nếu không có gói Premium, sử dụng giới hạn mặc định (3 bài)
        if not premium_package:
            return self.post_count < 3
            
        # Kiểm tra giới hạn từ gói Premium
        return self.post_count < premium_package.max_job_posts
        
    def can_view_cv(self):
        """
        Kiểm tra xem người dùng có thể xem CV không
        """
        if not self.is_premium or not self.is_employer():
            return False
            
        package = self.get_premium_package()
        if not package:
            return False
            
        # Reset counter nếu ngày khác
        today = timezone.now().date()
        if self.last_cv_view_date != today:
            self.cv_views_today = 0
            self.last_cv_view_date = today
            self.save(update_fields=['cv_views_today', 'last_cv_view_date'])
            
        return self.cv_views_today < package.max_cv_views_per_day
        
    def can_apply_job(self):
        """
        Kiểm tra xem ứng viên có thể ứng tuyển không
        """
        if self.is_employer():
            return False
            
        # Nếu không phải premium, cho phép ứng tuyển với giới hạn thấp
        if not self.is_premium:
            # Reset counter nếu ngày khác
            today = timezone.now().date()
            if self.last_application_date != today:
                self.job_applications_today = 0
                self.last_application_date = today
                self.save(update_fields=['job_applications_today', 'last_application_date'])
                
            # Người dùng thường chỉ được ứng tuyển 3 công việc mỗi ngày
            return self.job_applications_today < 3
            
        # Người dùng premium được ứng tuyển nhiều hơn
        package = self.get_premium_package()
        if not package:
            return self.job_applications_today < 3
            
        # Reset counter nếu ngày khác
        today = timezone.now().date()
        if self.last_application_date != today:
            self.job_applications_today = 0
            self.last_application_date = today
            self.save(update_fields=['job_applications_today', 'last_application_date'])
            
        return self.job_applications_today < package.daily_job_application_limit
        
    def can_chat_with_employers(self):
        """
        Kiểm tra xem người dùng có thể chat với nhà tuyển dụng không
        """
        if self.is_employer():
            return True  # Nhà tuyển dụng luôn được phép chat
            
        if not self.is_premium:
            return False  # Người dùng thường không được chat
            
        package = self.get_premium_package()
        if not package:
            return False
            
        return package.can_chat_with_employers
        
    def can_view_job_applications(self):
        """
        Kiểm tra xem người dùng có thể xem số người đã ứng tuyển vào công việc không
        """
        if not self.is_premium:
            return False
            
        package = self.get_premium_package()
        if not package:
            return False
            
        return package.can_view_job_applications

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
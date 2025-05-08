import logging
from django.shortcuts import redirect
from django.conf import settings
from social_core.exceptions import AuthAlreadyAssociated
from social_django.middleware import SocialAuthExceptionMiddleware
from .models import UserAccount
from rest_framework_simplejwt.tokens import RefreshToken

logger = logging.getLogger(__name__)

class CustomSocialAuthExceptionMiddleware(SocialAuthExceptionMiddleware):
    """
    Middleware tùy chỉnh để xử lý lỗi từ social auth,
    đặc biệt là AuthAlreadyAssociated
    """
    
    def process_exception(self, request, exception):
        """
        Xử lý các ngoại lệ từ social auth.
        Nếu là AuthAlreadyAssociated, tìm user đã tồn tại và đăng nhập.
        """
        logger.info(f"CustomSocialAuthExceptionMiddleware xử lý lỗi: {type(exception).__name__}")
        
        if isinstance(exception, AuthAlreadyAssociated):
            # Lấy thông tin email từ session
            email = request.session.get('email')
            logger.info(f"Xử lý AuthAlreadyAssociated cho email: {email}")
            
            # Lấy thông tin từ backend nếu có 
            if hasattr(exception, 'backend') and exception.backend:
                logger.info(f"Backend: {exception.backend}")
                
            # Lấy thông tin từ social nếu có
            if hasattr(exception, 'social') and exception.social:
                social = exception.social
                logger.info(f"Social: {social.provider} - User: {social.user.email if social.user else 'None'}")
                
                if social.user:
                    # Tạo token cho user
                    user = social.user
                    refresh = RefreshToken.for_user(user)
                    refresh["is_active"] = user.is_active
                    refresh["is_banned"] = getattr(user, 'is_banned', False)
                    role = "admin" if user.is_superuser else (user.get_role() if hasattr(user, 'get_role') else 'user')
                    refresh["role"] = role
                    
                    # Tạo URL redirect
                    redirect_url = f"{settings.FRONTEND_URL}?access_token={str(refresh.access_token)}&refresh_token={str(refresh)}&role={role}&email={user.email}"
                    logger.info(f"Redirect to: {redirect_url}")
                    return redirect(redirect_url)
            
            # Tìm user theo email
            if email:
                try:
                    user = UserAccount.objects.get(email=email)
                    logger.info(f"Tìm thấy user với email {email}")
                    
                    # Tạo token cho user
                    refresh = RefreshToken.for_user(user)
                    refresh["is_active"] = user.is_active
                    refresh["is_banned"] = getattr(user, 'is_banned', False)
                    role = "admin" if user.is_superuser else (user.get_role() if hasattr(user, 'get_role') else 'user')
                    refresh["role"] = role
                    
                    # Tạo URL redirect
                    redirect_url = f"{settings.FRONTEND_URL}?access_token={str(refresh.access_token)}&refresh_token={str(refresh)}&role={role}&email={user.email}"
                    logger.info(f"Redirect to: {redirect_url}")
                    return redirect(redirect_url)
                except UserAccount.DoesNotExist:
                    logger.error(f"Không tìm thấy user với email {email}")
        
        # Sử dụng xử lý mặc định nếu không phải AuthAlreadyAssociated
        return super().process_exception(request, exception) 
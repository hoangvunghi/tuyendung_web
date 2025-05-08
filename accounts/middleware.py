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
        logger.info(f"Exception message: {str(exception)}")
        
        if isinstance(exception, AuthAlreadyAssociated):
            # Lấy thông tin từ session
            email = request.session.get('email')
            user_id = request.session.get('user_id')
            logger.info(f"Xử lý AuthAlreadyAssociated - Email: {email}, User ID: {user_id}")
            
            # Cố gắng lấy thông tin chi tiết hơn từ exception
            social_account = None
            auth_provider = None
            
            # Lấy thông tin từ backend nếu có 
            backend = None
            if hasattr(exception, 'backend') and exception.backend:
                backend = exception.backend
                logger.info(f"Backend: {backend}")
                
                # Cố gắng lấy email từ backend
                if not email and hasattr(backend, 'data') and backend.data:
                    if 'email' in backend.data:
                        email = backend.data.get('email')
                        logger.info(f"Lấy được email từ backend: {email}")
                
            # Lấy thông tin từ exception.args
            if hasattr(exception, 'args') and exception.args:
                for arg in exception.args:
                    logger.info(f"Exception arg: {arg}")
                    if hasattr(arg, 'email') and arg.email:
                        email = arg.email
                        logger.info(f"Lấy được email từ arg: {email}")
                        
            # Lấy thông tin từ social nếu có
            if hasattr(exception, 'social') and exception.social:
                social = exception.social
                logger.info(f"Social: {social.provider} - User: {social.user.email if social.user else 'None'}")
                
                if social.user:
                    # Sử dụng user từ social
                    user = social.user
                    email = user.email
                    
                    # Tạo token và redirect
                    return self._create_token_and_redirect(user, email)
            
            # Lấy user từ user_id nếu có
            if user_id:
                try:
                    user = UserAccount.objects.get(id=user_id)
                    logger.info(f"Tìm thấy user từ user_id {user_id}: {user.email}")
                    
                    # Tạo token và redirect
                    return self._create_token_and_redirect(user, user.email)
                except UserAccount.DoesNotExist:
                    logger.error(f"Không tìm thấy user với ID: {user_id}")
            
            # Lấy user từ email nếu có
            if email:
                try:
                    user = UserAccount.objects.get(email=email)
                    logger.info(f"Tìm thấy user từ email {email}: {user.id}")
                    
                    # Tạo token và redirect
                    return self._create_token_and_redirect(user, email)
                except UserAccount.DoesNotExist:
                    logger.error(f"Không tìm thấy user với email: {email}")
            
            # Nếu không có thông tin, log để debug
            logger.error(f"Không đủ thông tin để xử lý AuthAlreadyAssociated: {vars(exception) if hasattr(exception, '__dict__') else str(exception)}")
        
        # Sử dụng xử lý mặc định nếu không phải AuthAlreadyAssociated hoặc không thể xử lý
        return super().process_exception(request, exception)

    def _create_token_and_redirect(self, user, email):
        """Helper để tạo token và URL redirect"""
        refresh = RefreshToken.for_user(user)
        refresh["is_active"] = user.is_active
        refresh["is_banned"] = getattr(user, 'is_banned', False)
        role = "admin" if user.is_superuser else (user.get_role() if hasattr(user, 'get_role') else 'user')
        refresh["role"] = role
        
        # Tạo URL redirect
        redirect_url = f"{settings.FRONTEND_URL}?access_token={str(refresh.access_token)}&refresh_token={str(refresh)}&role={role}&email={email}"
        logger.info(f"Redirect to: {redirect_url}")
        return redirect(redirect_url) 
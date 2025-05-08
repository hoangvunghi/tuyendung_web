import logging
from django.contrib.auth import get_user_model
from profiles.models import UserInfo
from accounts.models import UserAccount, Role, UserRole
from rest_framework_simplejwt.tokens import RefreshToken
from social_core.pipeline.social_auth import social_user
from social_core.exceptions import AuthAlreadyAssociated
from social_django.models import UserSocialAuth
from django.db.utils import IntegrityError
from django.contrib.auth.hashers import make_password

User = UserAccount
logger = logging.getLogger(__name__)

def associate_by_email(backend, details, user=None, *args, **kwargs):
    """Liên kết tài khoản nếu email đã tồn tại."""
    logger.info(f"Starting associate_by_email for email: {details.get('email')}")
    logger.info(f"Backend: {backend.name}")
    logger.info(f"Details: {details}")
    logger.info(f"User: {user}")
    
    if user:
        logger.info(f"User already logged in: {user.email}")
        return {'user': user}

    email = details.get('email')
    if not email:
        logger.error("No email provided in details")
        return None

    try:
        existing_user = User.objects.get(email=email)
        logger.info(f"Found existing user with email: {email}")
        return {'user': existing_user}
    except User.DoesNotExist:
        logger.info(f"No existing user found for email: {email}")
        return None

def custom_social_user(strategy, details, backend, uid, user=None, *args, **kwargs):
    """Pipeline tùy chỉnh để xử lý social user."""
    logger.info(f"Starting custom_social_user for backend: {backend.name}, uid: {uid}")
    logger.info(f"Details: {details}")
    logger.info(f"User: {user}")
    
    try:
        email = details.get('email')
        if not email:
            logger.error("No email provided in details")
            return None

        # Kiểm tra xem social auth đã tồn tại chưa
        try:
            social_auth = UserSocialAuth.objects.get(provider=backend.name, uid=uid)
            logger.info(f"Found existing social auth for uid: {uid}, user: {social_auth.user.email}")
            return {
                'user': social_auth.user,
                'is_new': False,
                'social_user': social_auth
            }
        except UserSocialAuth.DoesNotExist:
            logger.info(f"No existing social auth found for uid: {uid}")

        # Nếu đã có user từ các bước trước, sử dụng user đó
        if user:
            logger.info(f"Using existing user from previous steps: {user.email}")
            try:
                social_auth = UserSocialAuth.objects.create(
                    user=user,
                    provider=backend.name,
                    uid=uid,
                    extra_data=details
                )
                return {
                    'user': user,
                    'is_new': False,
                    'social_user': social_auth
                }
            except IntegrityError:
                social_auth = UserSocialAuth.objects.get(provider=backend.name, uid=uid)
                return {
                    'user': social_auth.user,
                    'is_new': False,
                    'social_user': social_auth
                }

        # Tìm user theo email
        try:
            existing_user = User.objects.get(email=email)
            logger.info(f"Found existing user by email: {email}")
            try:
                social_auth = UserSocialAuth.objects.create(
                    user=existing_user,
                    provider=backend.name,
                    uid=uid,
                    extra_data=details
                )
                return {
                    'user': existing_user,
                    'is_new': False,
                    'social_user': social_auth
                }
            except IntegrityError:
                social_auth = UserSocialAuth.objects.get(provider=backend.name, uid=uid)
                return {
                    'user': social_auth.user,
                    'is_new': False,
                    'social_user': social_auth
                }
        except User.DoesNotExist:
            logger.info(f"Creating new user for email: {email}")
            # Tạo user mới với email từ Google
            # Sử dụng email đầy đủ làm username thay vì chỉ lấy phần trước @
            user = User.objects.create(
                email=email,
                username=email,  # Sử dụng email đầy đủ làm username
                is_active=True,
                password=make_password("12345678")  # Mật khẩu mặc định là 12345678
            )
            social_auth = UserSocialAuth.objects.create(
                user=user,
                provider=backend.name,
                uid=uid,
                extra_data=details
            )
            return {
                'user': user,
                'is_new': True,
                'social_user': social_auth
            }

    except Exception as e:
        logger.error(f"Error in custom_social_user: {str(e)}", exc_info=True)
        return None

def create_user_profile(backend, user, response, *args, **kwargs):
    """Pipeline để tạo/cập nhật user profile sau khi đăng nhập Google."""
    if backend.name != 'google-oauth2':
        return None

    logger.info(f"Starting create_user_profile for user: {user.email}")
    try:
        # Lấy thông tin từ response
        fullname = response.get('name', '')
        if not fullname:
            fullname = f"{response.get('given_name', '')} {response.get('family_name', '')}".strip()
        if not fullname:
            fullname = user.email

        # Tạo UserInfo nếu chưa tồn tại
        UserInfo.objects.get_or_create(
            user=user,
            defaults={
                'fullname': fullname,
                'gender': 'male',
                'balance': 0.00,
                'cv_attachments_url': None
            }
        )

        # Gán role 'none' nếu chưa có role
        try:
            none_role = Role.objects.get(name='none')
            UserRole.objects.get_or_create(user=user, defaults={'role': none_role})
        except Role.DoesNotExist:
            logger.error("Role 'none' does not exist")
            none_role = Role.objects.create(name='none')
            UserRole.objects.get_or_create(user=user, defaults={'role': none_role})

        return {
            'user': user,
            'is_new': kwargs.get('is_new', False)
        }

    except Exception as e:
        logger.error(f"Error in create_user_profile: {str(e)}", exc_info=True)
        return None

def get_token_for_frontend(backend, user, response, *args, **kwargs):
    """Tạo JWT token và lưu vào session."""
    logger.info(f"Starting get_token_for_frontend for user: {user.email}")
    try:
        refresh = RefreshToken.for_user(user)
        refresh["is_active"] = user.is_active
        refresh["is_banned"] = user.is_banned
        role = "admin" if user.is_superuser else user.get_role()
        refresh["role"] = role
        
        # Lưu token vào session
        strategy = kwargs.get('strategy')
        if strategy and hasattr(strategy, 'session_set'):
            strategy.session_set('access_token', str(refresh.access_token))
            strategy.session_set('refresh_token', str(refresh))
            strategy.session_set('user_role', role)
            strategy.session_set('user_email', user.email)
            strategy.session_set('is_active', user.is_active)
            strategy.session_set('is_banned', user.is_banned)
            logger.info(f"Tokens saved to session for user: {user.email}")
        
        return {
            'access_token': str(refresh.access_token),
            'refresh_token': str(refresh),
            'role': role,
            'email': user.email,
            'is_active': user.is_active,
            'is_banned': user.is_banned
        }
    except Exception as e:
        logger.error(f"Error in get_token_for_frontend: {str(e)}", exc_info=True)
        return None

def handle_auth_already_associated(strategy, details, backend, uid, user=None, *args, **kwargs):
    """
    Pipeline xử lý trường hợp tài khoản đã được liên kết
    """
    logger.info(f"Starting handle_auth_already_associated for uid: {uid}")
    
    try:
        email = details.get('email')
        if not email:
            logger.error("No email provided in details")
            return None

        # Nếu đã có user, kiểm tra email có khớp không
        if user:
            if user.email != email:
                logger.error(f"Email mismatch: {user.email} != {email}")
                return None
            logger.info(f"Using existing user: {user.email}")
            try:
                social_user = UserSocialAuth.objects.create(
                    user=user,
                    provider=backend.name,
                    uid=uid,
                    extra_data=details
                )
                return {
                    'user': user,
                    'is_new': False,
                    'social_user': social_user
                }
            except IntegrityError:
                social_user = UserSocialAuth.objects.get(provider=backend.name, uid=uid)
                return {
                    'user': social_user.user,
                    'is_new': False,
                    'social_user': social_user
                }

        # Tìm user theo email
        try:
            existing_user = User.objects.get(email=email)
            logger.info(f"Found existing user by email: {email}")
            try:
                social_user = UserSocialAuth.objects.create(
                    user=existing_user,
                    provider=backend.name,
                    uid=uid,
                    extra_data=details
                )
                return {
                    'user': existing_user,
                    'is_new': False,
                    'social_user': social_user
                }
            except IntegrityError:
                social_user = UserSocialAuth.objects.get(provider=backend.name, uid=uid)
                return {
                    'user': social_user.user,
                    'is_new': False,
                    'social_user': social_user
                }
        except User.DoesNotExist:
            logger.info(f"No existing user found for email: {email}")
            return None

    except Exception as e:
        logger.error(f"Error in handle_auth_already_associated: {str(e)}", exc_info=True)
        return None
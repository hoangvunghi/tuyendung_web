import logging
from django.contrib.auth import get_user_model
from profiles.models import UserInfo
from accounts.models import UserAccount, Role, UserRole
from rest_framework_simplejwt.tokens import RefreshToken
from social_core.pipeline.social_auth import social_user
from social_core.exceptions import AuthAlreadyAssociated


User = get_user_model()
logger = logging.getLogger(__name__)

def associate_by_email(backend, details, user=None, *args, **kwargs):
    """Liên kết tài khoản nếu email đã tồn tại."""
    logger.info(f"Starting associate_by_email for email: {details.get('email')}")
    
    if user:
        logger.info("User already logged in, skipping association")
        return None

    email = details.get('email')
    if email:
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
    
    try:
        # Nếu user đã tồn tại, trả về luôn
        if user:
            logger.info(f"User already exists: {user.email}")
            return {
                'user': user,
                'is_new': False
            }

        # Tìm user theo email
        email = details.get('email')
        if not email:
            logger.error("No email provided in details")
            return None

        try:
            existing_user = User.objects.get(email=email)
            logger.info(f"Found existing user by email: {email}")
            return {
                'user': existing_user,
                'is_new': False
            }
        except User.DoesNotExist:
            logger.info(f"Creating new user for email: {email}")
            # Tạo user mới
            user = User.objects.create(
                email=email,
                username=email,
                first_name=details.get('first_name', ''),
                last_name=details.get('last_name', ''),
                is_active=True
            )
            return {
                'user': user,
                'is_new': True
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
        # Tạo UserInfo nếu chưa tồn tại
        UserInfo.objects.get_or_create(
            user=user,
            defaults={
                'fullname': f"{user.first_name} {user.last_name}".strip() or user.email,
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
        # Kiểm tra xem user đã tồn tại chưa
        if user:
            logger.info(f"User already exists: {user.email}")
            social_user, created = user.social_auth.get_or_create(
                provider=backend.name,
                uid=uid,
                defaults={'extra_data': details}
            )
            return {
                'user': user,
                'is_new': False,
                'social_user': social_user
            }

        # Tìm user theo email
        email = details.get('email')
        if email:
            try:
                existing_user = User.objects.get(email=email)
                logger.info(f"Found existing user by email: {email}")
                
                # Kiểm tra xem user đã liên kết với Google chưa
                if existing_user.social_auth.filter(provider='google-oauth2').exists():
                    logger.info(f"User {email} already associated with Google")
                    social_user = existing_user.social_auth.get(provider=backend.name)
                    return {
                        'user': existing_user,
                        'is_new': False,
                        'social_user': social_user
                    }
                else:
                    logger.info(f"User {email} not associated with Google yet")
                    social_user = existing_user.social_auth.create(
                        provider=backend.name,
                        uid=uid,
                        extra_data=details
                    )
                    return {
                        'user': existing_user,
                        'is_new': False,
                        'social_user': social_user
                    }
            except User.DoesNotExist:
                logger.info(f"No existing user found for email: {email}")

        # Tìm user theo social auth
        try:
            existing_user = User.objects.get(social_auth__provider=backend.name, social_auth__uid=uid)
            social_user = existing_user.social_auth.get(provider=backend.name, uid=uid)
            logger.info(f"Found existing user by social auth: {existing_user.email}")
            return {
                'user': existing_user,
                'is_new': False,
                'social_user': social_user
            }
        except User.DoesNotExist:
            logger.info(f"No existing user found for provider: {backend.name}, uid: {uid}")

        # Nếu không tìm thấy user, tạo mới
        if not user and not email:
            logger.error("No email provided in details")
            return None

        # Tạo user mới
        user = User.objects.create(
            email=email,
            username=email,
            first_name=details.get('first_name', ''),
            last_name=details.get('last_name', ''),
            is_active=True
        )
        logger.info(f"Created new user: {email}")

        # Tạo social auth cho user mới
        social_user = user.social_auth.create(
            provider=backend.name,
            uid=uid,
            extra_data=details
        )

        return {
            'user': user,
            'is_new': True,
            'social_user': social_user
        }

    except Exception as e:
        logger.error(f"Error in handle_auth_already_associated: {str(e)}", exc_info=True)
        # Trả về None để pipeline dừng lại và hiển thị lỗi
        return None
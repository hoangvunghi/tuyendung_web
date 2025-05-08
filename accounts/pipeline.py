import logging
from django.contrib.auth import get_user_model
from profiles.models import UserInfo
from accounts.models import UserAccount, Role, UserRole
from rest_framework_simplejwt.tokens import RefreshToken
from social_core.pipeline.social_auth import social_user
from social_core.exceptions import AuthAlreadyAssociated


User = get_user_model()
logger = logging.getLogger(__name__)

def create_user_profile(backend, user, response, *args, **kwargs):
    """
    Pipeline to create/update user profile after Google login
    """
    if backend.name != 'google-oauth2':
        logger.info("Backend is not google-oauth2, skipping create_user_profile")
        return None

    logger.info(f"Starting create_user_profile for Google user: {response.get('email', 'unknown')}")
    try:
        # Validate response
        email = response.get('email')
        if not email:
            logger.error("No email provided in Google OAuth2 response")
            raise ValueError("Email is required from Google OAuth2 response")

        first_name = response.get('given_name', '')
        last_name = response.get('family_name', '')
        google_id = response.get('sub')

        # Find or create user
        try:
            user = User.objects.get(email=email)
            logger.info(f"Existing user found: {email}")
            user.social_auth.update_or_create(
                provider='google-oauth2',
                uid=google_id,
                defaults={'extra_data': response}
            )
        except User.DoesNotExist:
            logger.info(f"Creating new user for email: {email}")
            user = User.objects.create(
                email=email,
                username=email,
                first_name=first_name,
                last_name=last_name,
                is_active=True
            )
            user.social_auth.create(
                provider='google-oauth2',
                uid=google_id,
                extra_data=response
            )

        # Create UserInfo if not exists
        UserInfo.objects.get_or_create(
            user=user,
            defaults={
                'fullname': f"{first_name} {last_name}",
                'gender': 'male',
                'balance': 0.00,
                'cv_attachments_url': None
            }
        )

        # Assign 'none' role if no role exists
        try:
            none_role = Role.objects.get(name='none')
            UserRole.objects.get_or_create(user=user, defaults={'role': none_role})
        except Role.DoesNotExist:
            logger.error("Role 'none' does not exist in the database")
            raise ValueError("Role 'none' is required but not found")

        # Generate tokens
        refresh = RefreshToken.for_user(user)
        role = user.get_role()
        logger.info(f"User profile created/updated for {user.email}. Role: {role}")

        return {
            'user': user,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            },
            'role': role,
            'is_active': user.is_active,
            'is_banned': getattr(user, 'is_banned', False)
        }

    except Exception as e:
        logger.error(f"Error in create_user_profile for {response.get('email', 'unknown')}: {str(e)}", exc_info=True)
        raise  # Re-raise to halt pipeline and debug
def get_token_for_frontend(backend, user, response, *args, **kwargs):
    """
    Tạo JWT token và thêm vào session
    """
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
        else:
            logger.warning(f"Strategy not found or invalid for user: {user.email}. Cannot save tokens to session.")
            
        return {
            'access_token': str(refresh.access_token),
            'refresh_token': str(refresh),
            'role': role,
            'email': user.email,
            'is_active': user.is_active,
            'is_banned': user.is_banned
        }
    except Exception as e:
        logger.error(f"Error in get_token_for_frontend for user: {user.email}: {str(e)}", exc_info=True)
        return None
def associate_by_email(backend, details, user=None, *args, **kwargs):
    """Liên kết tài khoản nếu email đã tồn tại.
    """
    if user:
        return None # User đã đăng nhập, không cần làm gì

    email = details.get('email')
    if email:
        try:
            existing_user = User.objects.get(email=email)
            # Kiểm tra xem tài khoản hiện có đã liên kết với Google chưa
            if not existing_user.social_auth.filter(provider='google-oauth2').exists():
                return {'user': existing_user}
        except User.DoesNotExist:
            pass
    return None

def handle_auth_already_associated(strategy, details, backend, uid, user=None, *args, **kwargs):
    """
    Pipeline xử lý trường hợp tài khoản đã được liên kết
    """
    try:
        # Thử liên kết tài khoản
        return social_user(strategy, details, backend, uid, user, *args, **kwargs)
    except AuthAlreadyAssociated:
        # Nếu tài khoản đã được liên kết, tìm user theo email
        email = details.get('email')
        if email:
            try:
                # Tìm user theo email
                existing_user = User.objects.get(email=email)
                
                # Tạo token cho user đã liên kết
                refresh = RefreshToken.for_user(existing_user)
                role = existing_user.get_role()
                
                # Trả về thông tin user và token
                return {
                    'user': existing_user,
                    'tokens': {
                        'refresh': str(refresh),
                        'access': str(refresh.access_token),
                    },
                    'role': role,
                    'is_active': existing_user.is_active,
                    'is_banned': existing_user.is_banned,
                    'is_new': False
                }
            except User.DoesNotExist:
                pass
        return None

def custom_social_user(strategy, details, backend, uid, user=None, *args, **kwargs):
    """
    Custom pipeline to wrap social_user and handle errors
    """
    logger.info(f"Starting custom_social_user with strategy: {type(strategy)}, backend: {type(backend)}, uid: {uid}, user: {user}")
    if not hasattr(backend, 'name'):
        logger.error(f"Backend is not a valid backend object: {backend}. Expected a backend with 'name' attribute.")
        raise ValueError("Invalid backend object passed to custom_social_user")

    logger.info(f"Processing backend: {backend.name}, uid: {uid}")
    try:
        result = social_user(strategy, details, backend, uid, user, *args, **kwargs)
        logger.info(f"custom_social_user result: {result}")
        return result
    except AuthAlreadyAssociated:
        logger.warning(f"AuthAlreadyAssociated for uid: {uid}, backend: {backend.name}")
        existing_user = User.objects.filter(
            social_auth__provider=backend.name,
            social_auth__uid=uid
        ).first()
        if existing_user:
            logger.info(f"Found existing user: {existing_user.email}")
            return {
                'user': existing_user,
                'is_new': False
            }
        logger.error(f"No user found for uid: {uid}, backend: {backend.name}")
        raise
    except Exception as e:
        logger.error(f"Error in custom_social_user for uid: {uid}, backend: {backend.name}: {str(e)}", exc_info=True)
        raise
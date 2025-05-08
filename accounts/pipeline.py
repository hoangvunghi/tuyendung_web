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
    Pipeline để tạo profile cho user sau khi đăng nhập Google
    """
    if backend.name == 'google-oauth2':
        logger.info(f"Starting create_user_profile for Google user: {response.get('email')}")
        try:
            # Lấy thông tin từ Google
            email = response.get('email', '')
            if not email:
                logger.error("No email provided in Google response")
                return None
                
            first_name = response.get('given_name', '')
            last_name = response.get('family_name', '')
            google_id = response.get('sub')
            
            if not google_id:
                logger.error("No Google ID provided in response")
                return None
            
            logger.info(f"Processing user with email: {email}, google_id: {google_id}")
            
            # Tìm user theo email
            try:
                existing_user = User.objects.get(email=email)
                logger.info(f"Found existing user: {email}")
                # Nếu user đã tồn tại, cập nhật google_id
                social_auth, created = existing_user.social_auth.update_or_create(
                    provider='google-oauth2',
                    uid=google_id,
                    defaults={'extra_data': response}
                )
                logger.info(f"Social auth {'created' if created else 'updated'} for user {email}")
                user = existing_user
            except User.DoesNotExist:
                logger.info(f"Creating new user for email: {email}")
                # Nếu user chưa tồn tại, tạo mới
                user = User.objects.create(
                    email=email,
                    username=email,
                    first_name=first_name,
                    last_name=last_name,
                    is_active=True
                )
                social_auth = user.social_auth.create(
                    provider='google-oauth2',
                    uid=google_id,
                    extra_data=response
                )
                logger.info(f"Created new user and social auth for {email}")
            
            if not user:
                logger.error("Failed to create or find user")
                return None
                
            # Tạo profile nếu chưa có
            try:
                user_info, created = UserInfo.objects.get_or_create(
                    user=user,
                    defaults={
                        'fullname': f"{first_name} {last_name}",
                        'gender': "male",
                        'balance': 0.00,
                        'cv_attachments_url': None
                    }
                )
                logger.info(f"UserInfo {'created' if created else 'already exists'} for {email}")
            except Exception as e:
                logger.error(f"Error creating UserInfo for {email}: {str(e)}")
                return None
                
            # Tạo role none nếu chưa có
            try:
                none_role, created = Role.objects.get_or_create(name='none')
                logger.info(f"Role 'none' {'created' if created else 'already exists'}")
                
                user_role, created = UserRole.objects.get_or_create(
                    user=user,
                    defaults={'role': none_role}
                )
                logger.info(f"UserRole {'created' if created else 'already exists'} for {email}")
            except Exception as e:
                logger.error(f"Error creating Role/UserRole for {email}: {str(e)}")
                return None
                
            # Tạo token
            try:
                refresh = RefreshToken.for_user(user)
                role = user.get_role()
                logger.info(f"Generated tokens for {email} with role: {role}")
                
                return {
                    'user': user,
                    'tokens': {
                        'refresh': str(refresh),
                        'access': str(refresh.access_token),
                    },
                    'role': role,
                    'is_active': user.is_active,
                    'is_banned': user.is_banned
                }
            except Exception as e:
                logger.error(f"Error generating tokens for {email}: {str(e)}")
                return None
            
        except Exception as e:
            logger.error(f"Error in create_user_profile for {response.get('email')}: {str(e)}", exc_info=True)
            return None
    return None

def get_token_for_frontend(backend, user, response, *args, **kwargs):
    """
    Tạo JWT token và thêm vào session
    """
    if backend.name == 'google-oauth2':
        logger.info(f"Starting get_token_for_frontend for user: {user.email if user else 'None'}")
        
        if not user:
            logger.error("User is None in get_token_for_frontend")
            return None
            
        try:
            refresh = RefreshToken.for_user(user)
            refresh["is_active"] = user.is_active
            refresh["is_banned"] = user.is_banned
            role = "admin" if user.is_superuser else user.get_role()
            refresh["role"] = role
            
            logger.info(f"Generated tokens for {user.email} with role: {role}")
            
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
                logger.warning("Strategy not found or invalid. Cannot save tokens to session.")
                
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
    return None

def associate_by_email(backend, details, user=None, *args, **kwargs):
    """Liên kết tài khoản nếu email đã tồn tại.
    """
    logger.info(f"Starting associate_by_email for email: {details.get('email')}")
    
    if user:
        logger.info("User already logged in, skipping association")
        return None

    email = details.get('email')
    if email:
        try:
            existing_user = User.objects.get(email=email)
            logger.info(f"Found existing user with email: {email}")
            # Kiểm tra xem tài khoản hiện có đã liên kết với Google chưa
            if not existing_user.social_auth.filter(provider='google-oauth2').exists():
                logger.info(f"Associating existing user {email} with Google")
                return {'user': existing_user}
            else:
                logger.info(f"User {email} already associated with Google")
        except User.DoesNotExist:
            logger.info(f"No existing user found for email: {email}")
    return None

def handle_auth_already_associated(strategy, details, backend, uid, user=None, *args, **kwargs):
    """
    Pipeline xử lý trường hợp tài khoản đã được liên kết
    """
    logger.info(f"Starting handle_auth_already_associated for uid: {uid}")
    
    try:
        # Thử liên kết tài khoản
        result = social_user(strategy, details, backend, uid, user, *args, **kwargs)
        logger.info("Successfully associated account")
        return result
    except AuthAlreadyAssociated:
        logger.info("AuthAlreadyAssociated exception caught")
        # Nếu tài khoản đã được liên kết, tìm user theo email
        email = details.get('email')
        if email:
            try:
                # Tìm user theo email
                existing_user = User.objects.get(email=email)
                logger.info(f"Found existing user: {email}")
                
                # Tạo token cho user đã liên kết
                refresh = RefreshToken.for_user(existing_user)
                role = existing_user.get_role()
                logger.info(f"Generated tokens for {email} with role: {role}")
                
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
                logger.error(f"User not found for email: {email}")
                pass
        return None

def custom_social_user(strategy, details, backend, uid, user=None, *args, **kwargs):
    """
    Pipeline tùy chỉnh để xử lý social user
    """
    logger.info(f"Starting custom_social_user for backend: {backend.name}, uid: {uid}")
    
    try:
        # Gọi hàm social_user gốc
        result = social_user(strategy, details, backend, uid, user, *args, **kwargs)
        if result and isinstance(result, dict) and 'user' in result:
            logger.info(f"Successfully got user from social_user: {result['user'].email}")
            return result
        logger.warning("social_user did not return expected result")
        return None
        
    except AuthAlreadyAssociated:
        logger.info(f"AuthAlreadyAssociated for uid: {uid}")
        try:
            # Nếu tài khoản đã liên kết, tìm user hiện tại
            existing_user = User.objects.get(social_auth__provider=backend.name, social_auth__uid=uid)
            if existing_user:
                logger.info(f"Found existing user: {existing_user.email}")
                # Trả về user hiện tại để pipeline tiếp tục
                return {
                    'user': existing_user,
                    'is_new': False
                }
            logger.warning(f"No user found for provider: {backend.name}, uid: {uid}")
            return None
        except User.DoesNotExist:
            logger.error(f"User not found for provider: {backend.name}, uid: {uid}")
            return None
        except Exception as e:
            logger.error(f"Error in custom_social_user: {str(e)}", exc_info=True)
            return None
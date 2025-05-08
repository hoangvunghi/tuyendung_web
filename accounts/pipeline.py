import logging
from django.contrib.auth import get_user_model
from profiles.models import UserInfo
from accounts.models import UserAccount, Role, UserRole
from rest_framework_simplejwt.tokens import RefreshToken
from social_core.pipeline.social_auth import social_user
from social_core.exceptions import AuthAlreadyAssociated, AuthException
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

def auth_allowed(backend, details, response, *args, **kwargs):
    """Ghi đè hàm xử lý lỗi AuthAlreadyAssociated để cho phép đăng nhập với tài khoản có email trùng."""
    if not backend.auth_allowed(response, details):
        return False
    
    email = details.get('email')
    if not email:
        return False
    
    # Nếu đã có user với email này, cho phép đăng nhập
    try:
        existing_user = User.objects.get(email=email)
        logger.info(f"Auth allowed: Found existing user with email {email}")
        return True
    except User.DoesNotExist:
        # Không có user với email này, tiếp tục pipeline bình thường
        pass
    
    return True

def social_auth_exception(backend, strategy, details, response, uid=None, user=None, social=None, *args, **kwargs):
    """
    Xử lý ngoại lệ trong quá trình Social Auth.
    Hàm này được gọi khi có ngoại lệ xảy ra trong pipeline.
    Nếu là AuthAlreadyAssociated, tìm user đang tồn tại và đăng nhập.
    """
    logger.info(f"Social Auth Exception Handler được gọi")
    
    # Lấy ngoại lệ
    if 'exception' not in kwargs:
        logger.error("No exception in kwargs")
        return None
    
    exception = kwargs['exception']
    logger.info(f"Exception type: {type(exception).__name__}, message: {str(exception)}")
    
    # Xử lý AuthAlreadyAssociated
    if isinstance(exception, AuthAlreadyAssociated):
        logger.info(f"Processing AuthAlreadyAssociated for: {details.get('email', 'no-email')}")
        
        # Nếu có thông tin về social auth gây lỗi
        if social:
            logger.info(f"Social auth info: provider={social.provider}, user={social.user.email if social.user else 'None'}")
            if social.user:
                # Lưu thông tin user vào session để xử lý ở hàm error view
                if strategy and hasattr(strategy, 'session_set'):
                    strategy.session_set('auth_already_user_id', social.user.id)
                    strategy.session_set('auth_already_email', social.user.email)
                    logger.info(f"Saved user info to session: {social.user.id}, {social.user.email}")
                return social.user
        
        # Tìm user theo email
        email = details.get('email')
        if email:
            try:
                user = User.objects.get(email=email)
                logger.info(f"Found existing user with email {email}")
                
                # Lưu thông tin user vào session
                if strategy and hasattr(strategy, 'session_set'):
                    strategy.session_set('auth_already_user_id', user.id)
                    strategy.session_set('auth_already_email', user.email)
                    logger.info(f"Saved user info to session: {user.id}, {user.email}")
                
                # Redirect về trang lỗi nhưng với thông tin để xử lý đăng nhập
                redirect_url = f"{strategy.build_absolute_uri('/api/auth/error/')}?error_type=AuthAlreadyAssociated&email={email}"
                logger.info(f"Redirecting to: {redirect_url}")
                
                # Trả về user để social auth không raise exception nữa
                return user
            except User.DoesNotExist:
                logger.error(f"No user found with email {email}")
    
    # Log chi tiết về exception để debug
    logger.error(f"Exception details: {vars(exception) if hasattr(exception, '__dict__') else str(exception)}")
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

        # Nếu đã có user từ các bước trước, sử dụng user đó
        if user:
            logger.info(f"Using existing user from previous steps: {user.email}")
            
            # Kiểm tra xem social auth đã tồn tại cho user này chưa
            try:
                social_auth = UserSocialAuth.objects.get(user=user, provider=backend.name)
                logger.info(f"User already has social auth for this provider")
                return {
                    'user': user,
                    'is_new': False,
                    'social_user': social_auth
                }
            except UserSocialAuth.DoesNotExist:
                # Tạo social auth mới cho user này
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
                    # Nếu có lỗi integrity, tìm kiếm social auth đã tồn tại
                    social_auth = UserSocialAuth.objects.get(provider=backend.name, uid=uid)
                    return {
                        'user': social_auth.user,
                        'is_new': False,
                        'social_user': social_auth
                    }

        # Tìm kiếm social auth theo uid và provider
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

        # Tìm user theo email
        try:
            existing_user = User.objects.get(email=email)
            logger.info(f"Found existing user by email: {email}")
            
            # Tạo social auth cho user đã tồn tại
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
                # Nếu có lỗi integrity, tìm kiếm social auth đã tồn tại
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
            
            # Tạo social auth cho user mới
            social_auth = UserSocialAuth.objects.create(
                user=user,
                provider=backend.name,
                uid=uid,
                extra_data=details
            )
            
            # Tạo role 'none' cho user mới
            try:
                none_role = Role.objects.get(name='none')
            except Role.DoesNotExist:
                none_role = Role.objects.create(name='none')
            
            UserRole.objects.create(user=user, role=none_role)
            
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

def save_email_to_session(strategy, details, backend, response, *args, **kwargs):
    """
    Lưu email từ social provider vào session để có thể sử dụng sau này
    (đặc biệt là khi xử lý lỗi AuthAlreadyAssociated)
    """
    email = details.get('email')
    
    # Debug thông tin nhận được
    logger.info(f"save_email_to_session - Email từ details: {email}")
    logger.info(f"save_email_to_session - Backend: {backend.__class__.__name__}")
    logger.info(f"save_email_to_session - Details: {details}")
    
    # Lưu email vào session
    if email and strategy and hasattr(strategy, 'session_set'):
        logger.info(f"Saving email to session: {email}")
        strategy.session_set('email', email)
        
        # Kiểm tra xem email đã được lưu chưa
        saved_email = strategy.session_get('email')
        logger.info(f"Email đã lưu trong session: {saved_email}")
    else:
        logger.warning(f"Không thể lưu email vào session: email={email}, strategy={strategy}")
    
    # Lấy user từ email nếu có
    if email:
        try:
            from .models import UserAccount
            user = UserAccount.objects.get(email=email)
            logger.info(f"Tìm thấy user cho email {email}: {user.id}")
            
            # Lưu thông tin user vào session
            if strategy and hasattr(strategy, 'session_set'):
                strategy.session_set('user_id', user.id)
                logger.info(f"Đã lưu user_id vào session: {user.id}")
        except Exception as e:
            logger.error(f"Lỗi khi tìm user theo email: {str(e)}")
    
    return None

def extract_email_from_google(strategy, details, response, backend, *args, **kwargs):
    """
    Trích xuất email từ response của Google OAuth2 và lưu vào session.
    Hàm này được chạy trước khi social_user để đảm bảo email được lưu vào session.
    """
    logger.info(f"extract_email_from_google được gọi")
    
    # Debug thông tin
    logger.info(f"Backend name: {backend.name}")
    logger.info(f"Details: {details}")
    
    # Chỉ xử lý nếu là backend Google
    if backend.name != 'google-oauth2':
        logger.info(f"Không phải Google OAuth2, bỏ qua")
        return None
    
    # Lấy email từ details
    email = details.get('email')
    logger.info(f"Email từ details: {email}")
    
    # Lưu email vào session
    if email and strategy and hasattr(strategy, 'session_set'):
        strategy.session_set('email', email)
        logger.info(f"Lưu email vào session: {email}")
    
    # Lấy thông tin từ response
    if response:
        logger.info(f"Response keys: {response.keys() if isinstance(response, dict) else 'not a dict'}")
        
        # Lấy email từ response nếu có
        if isinstance(response, dict):
            if 'email' in response:
                email = response.get('email')
                logger.info(f"Email từ response: {email}")
                
                # Lưu vào session
                if email and strategy and hasattr(strategy, 'session_set'):
                    strategy.session_set('email', email)
                    logger.info(f"Lưu email từ response vào session: {email}")
    
    return None
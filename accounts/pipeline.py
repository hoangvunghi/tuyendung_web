import logging
from django.contrib.auth import get_user_model
from profiles.models import UserInfo
from accounts.models import UserAccount, Role, UserRole
from rest_framework_simplejwt.tokens import RefreshToken

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
            first_name = response.get('given_name', '')
            last_name = response.get('family_name', '')
            google_id = response.get('sub')
            
            # Tìm user theo email
            try:
                existing_user = User.objects.get(email=email)
                # Nếu user đã tồn tại, cập nhật google_id
                existing_user.social_auth.update_or_create(
                    provider='google-oauth2',
                    uid=google_id,
                    defaults={'extra_data': response}
                )
                user = existing_user
            except User.DoesNotExist:
                # Nếu user chưa tồn tại, tạo mới
                user = User.objects.create(
                    email=email,
                    username=email,
                    is_active=True
                )
                user.social_auth.create(
                    provider='google-oauth2',
                    uid=google_id,
                    extra_data=response
                )
            
            # Tạo profile nếu chưa có
            if not UserInfo.objects.filter(user=user).exists():
                UserInfo.objects.create(
                    user=user,
                    fullname=f"{first_name} {last_name}",
                    gender="male",
                    balance=0.00,
                    cv_attachments_url=None
                )
            none_role = Role.objects.get(name='none')
            # nếu mà user không có role thì tạo role none
            if not UserRole.objects.filter(user=user).exists():
                UserRole.objects.create(user=user, role=none_role)
            # Tạo token
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
                'is_banned': user.is_banned
            }
        except Exception as e:
            logger.error(f"Error in create_user_profile for {response.get('email')}: {str(e)}", exc_info=True)
            return None
    return None

def get_token_for_frontend(backend, user, response, *args, **kwargs):
    """
    Tạo JWT token và thêm vào session
    """
    if backend.name == 'google-oauth2':
        logger.info(f"Starting get_token_for_frontend for user: {user.email}")
        try:
            refresh = RefreshToken.for_user(user)
            refresh["is_active"] = user.is_active
            refresh["is_banned"] = user.is_banned
            role = "admin" if user.is_superuser else user.get_role()
            refresh["role"] = role
            
            strategy = kwargs.get('strategy')
            if strategy:
                strategy.session_set('access_token', str(refresh.access_token))
                strategy.session_set('refresh_token', str(refresh))
                strategy.session_set('user_role', role)
                strategy.session_set('user_email', user.email)
                logger.info(f"Tokens saved to session for user: {user.email}")
            else:
                logger.warning(f"Strategy not found in kwargs for user: {user.email}. Cannot save tokens to session.")
        except Exception as e:
            logger.error(f"Error in get_token_for_frontend for user: {user.email}: {str(e)}", exc_info=True)

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
    try:
        # Gọi hàm social_user gốc
        result = social_user(strategy, details, backend, uid, user, *args, **kwargs)
        return result
    except AuthAlreadyAssociated:
        # Nếu tài khoản đã liên kết, tìm user hiện tại
        existing_user = User.objects.get(social_auth__provider=backend.name, social_auth__uid=uid)
        if existing_user:
            # Trả về user hiện tại để pipeline tiếp tục
            return {
                'user': existing_user,
                'is_new': False
            }
        raise  # Nếu không tìm thấy user, ném lỗi tiếp
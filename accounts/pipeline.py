from django.contrib.auth import get_user_model
from profiles.models import UserInfo
from social_core.exceptions import AuthAlreadyAssociated
from django.db import IntegrityError
from accounts.models import UserAccount, Role, UserRole
from rest_framework_simplejwt.tokens import RefreshToken
User = get_user_model()

def create_user_profile(backend, user, response, *args, **kwargs):
    """
    Pipeline để tạo profile cho user sau khi đăng nhập Google
    """
    if backend.name == 'google-oauth2':
        try:
            # Lấy thông tin từ Google
            email = response.get('email', '')
            first_name = response.get('given_name', '')
            last_name = response.get('family_name', '')
            google_id = response.get('sub')
            
            # Kiểm tra xem UserProfile đã tồn tại chưa
            if not hasattr(user, 'userprofile'):
                if not UserInfo.objects.filter(user=user).exists():
                    UserInfo.objects.create(
                        user=user,
                        fullname=first_name + " " + last_name,
                        gender="male",
                        balance=0.00,
                        cv_attachments_url=None
                )
                else:
                    pass
            else:
                pass
            
            # Tạo hoặc cập nhật UserAccount
            user_account, created = UserAccount.objects.get_or_create(
                email=email,
                defaults={
                    'username': email,
                    'is_active': True,
                    'google_id': google_id
                }
            )
            
            if not created:
                user_account.is_active = True
                user_account.save()
            
            # Tạo hoặc lấy các role
            candidate_role, _ = Role.objects.get_or_create(name='candidate')
            employer_role, _ = Role.objects.get_or_create(name='employer')
            
            # Gán role dựa trên email domain
            if email.endswith('gmail.com'):
                if not UserRole.objects.filter(user=user_account, role=employer_role).exists():
                    UserRole.objects.create(user=user_account, role=employer_role)
            else:
                if not UserRole.objects.filter(user=user_account, role=candidate_role).exists():
                    UserRole.objects.create(user=user_account, role=candidate_role)

            # Tạo tokens
            refresh = RefreshToken.for_user(user_account)
            role = user_account.get_role()
            print("--------------------------------")
            print(role)
            print(refresh)
            print("--------------------------------")
            return {
                'user': user_account,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                },
                'role': role,
                'is_active': user_account.is_active,
                'is_banned': user_account.is_banned
            }
            
        except IntegrityError as e:
            if 'email' in str(e):
                existing_user = User.objects.get(email=email)
                if not existing_user.social_auth.filter(provider='google-oauth2').exists():
                    # Liên kết tài khoản Google với tài khoản hiện có
                    existing_user.social_auth.create(
                        provider='google-oauth2',
                        uid=response.get('sub'),
                        extra_data=response
                    )
                    # Cập nhật thông tin user
                    existing_user.first_name = first_name
                    existing_user.last_name = last_name
                    existing_user.is_active = True
                    existing_user.save()
                    
                    # Gán role dựa trên email domain
                    if email.endswith('gmail.com'):
                        if not UserRole.objects.filter(user=existing_user, role=employer_role).exists():
                            UserRole.objects.create(user=existing_user, role=employer_role)
                    else:
                        if not UserRole.objects.filter(user=existing_user, role=candidate_role).exists():
                            UserRole.objects.create(user=existing_user, role=candidate_role)
                    
                    # Tạo tokens
                    refresh = RefreshToken.for_user(existing_user)
                    role = existing_user.get_role()
                    print("--------------------------------")
                    print(role)
                    print(refresh)
                    print("--------------------------------")
                    return {
                        'user': existing_user,
                        'tokens': {
                            'refresh': str(refresh),
                            'access': str(refresh.access_token),
                        },
                        'role': role,
                        'is_active': existing_user.is_active,
                        'is_banned': existing_user.is_banned
                    }
                else:
                    # Nếu đã liên kết rồi thì cho phép đăng nhập
                    refresh = RefreshToken.for_user(existing_user)
                    role = existing_user.get_role()
                    print("--------------------------------")
                    print(role)
                    print(refresh)
                    print("--------------------------------")
                    # lưu refresh token vào local storage
                    
                    return {
                        'user': existing_user,
                        'tokens': {
                            'refresh': str(refresh),
                            'access': str(refresh.access_token),
                        },
                        'role': role,
                        'is_active': existing_user.is_active,
                        'is_banned': existing_user.is_banned
                    }
            raise
        except AuthAlreadyAssociated:
            # Nếu tài khoản đã được liên kết, lấy user hiện tại và cho phép đăng nhập
            existing_user = User.objects.get(social_auth__uid=response.get('sub'))
            refresh = RefreshToken.for_user(existing_user)
            role = existing_user.get_role()
            return {
                'user': existing_user,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                },
                'role': role,
                'is_active': existing_user.is_active,
                'is_banned': existing_user.is_banned
            }
            
    return None

def get_token_for_frontend(backend, user, response, *args, **kwargs):
    """
    Tạo JWT token và thêm vào session để view redirect có thể lấy.
    """
    if backend.name == 'google-oauth2':
        refresh = RefreshToken.for_user(user)
        refresh["is_active"] = user.is_active
        refresh["is_banned"] = user.is_banned
        role = "admin" if user.is_superuser else user.get_role()
        refresh["role"] = role
        
        # Lưu token vào session để view redirect xử lý
        strategy = kwargs.get('strategy')
        if strategy:
            strategy.session_set('access_token', str(refresh.access_token))
            strategy.session_set('refresh_token', str(refresh))
            strategy.session_set('user_role', role)
            strategy.session_set('user_email', user.email)
        else:
            pass

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
                # Liên kết tài khoản Google với tài khoản hiện có
                # Lưu ý: Cần đảm bảo người dùng thực sự sở hữu email này
                # Có thể yêu cầu xác thực thêm nếu cần
                return {'user': existing_user}
        except User.DoesNotExist:
            pass
    return None


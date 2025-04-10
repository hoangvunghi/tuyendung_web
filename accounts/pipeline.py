from django.contrib.auth import get_user_model
from profiles.models import UserInfo
from social_core.exceptions import AuthAlreadyAssociated
from django.db import IntegrityError

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
            picture = response.get('picture', '')
            
            # Kiểm tra xem user đã có profile chưa
            if not hasattr(user, 'profile'):
                # Tạo profile với thông tin cơ bản
                UserInfo.objects.create(
                    user=user,
                    fullname=first_name + " " + last_name,
                    gender="male",
                    balance=0.00,
                    cv_attachments_url=picture,
                )
            
            # Cập nhật thông tin user
            user.first_name = first_name
            user.last_name = last_name
            user.email = email
            user.save()
            
        except IntegrityError as e:
            if 'email' in str(e):
                existing_user = get_user_model().objects.get(email=email)
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
                    existing_user.save()
                    return {'user': existing_user}
                else:
                    # Nếu đã liên kết rồi thì cho phép đăng nhập
                    return {'user': existing_user}
            raise
            
    return None


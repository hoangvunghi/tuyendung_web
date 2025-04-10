from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from social_django.utils import psa
from accounts.models import UserAccount
from django.urls import reverse
from django.conf import settings
import requests

@api_view(['GET'])
@permission_classes([AllowAny])
def google_login_start(request):
    backend = 'google-oauth2'
    auth_url = reverse('social:begin', args=[backend])
    full_auth_url = request.build_absolute_uri(auth_url)
    return Response({
        'message': 'Redirect to Google login',
        'status': status.HTTP_200_OK,
        'auth_url': full_auth_url
    }, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([AllowAny])
def google_login_callback(request):
    code = request.data.get('code')
    print(code)
    if not code:
        return Response({
            'message': 'Code is required',
            'status': status.HTTP_400_BAD_REQUEST
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        # Get token from Google
        token_url = 'https://oauth2.googleapis.com/token'
        token_response = requests.post(token_url, data={
            'code': code,
            'client_id': settings.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY,
            'client_secret': settings.SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET,
            'redirect_uri': settings.SOCIAL_AUTH_GOOGLE_OAUTH2_REDIRECT_URI,
            'grant_type': 'authorization_code'
        })
        token_data = token_response.json()
        print("Token Response:", token_data)  # In ra response để debug
        
        if 'access_token' not in token_data:
            return Response({
                'message': f'Google authentication failed: {token_data.get("error_description", "Unknown error")}',
                'status': status.HTTP_401_UNAUTHORIZED
            }, status=status.HTTP_401_UNAUTHORIZED)

        # Get user info from Google
        user_info_url = 'https://www.googleapis.com/oauth2/v3/userinfo'
        user_info = requests.get(user_info_url, headers={'Authorization': f'Bearer {token_data["access_token"]}'})
        user_data = user_info.json()

        # Find or create user
        email = user_data.get('email')
        if not email:
            return Response({
                'message': 'Email not provided by Google',
                'status': status.HTTP_400_BAD_REQUEST
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = UserAccount.objects.get(email=email)
        except UserAccount.DoesNotExist:
            # Create new user
            username = email.split('@')[0]
            user = UserAccount.objects.create_user(
                email=email,
                username=username,
                is_active=True  # Google-authenticated users are automatically activated
            )

        if user.is_banned:
            return Response({
                'message': 'Tài khoản đã bị vô hiệu hóa. Vui lòng liên hệ quản trị viên để biết thêm thông tin.',
                'status': status.HTTP_401_UNAUTHORIZED
            }, status=status.HTTP_401_UNAUTHORIZED)

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        refresh["is_active"] = user.is_active
        refresh["is_banned"] = user.is_banned
        role = "admin" if user.is_superuser else user.get_role()
        refresh["role"] = role

        # Print tokens for debugging
        print("=== Google Login Success ===")
        print(f"Access Token: {str(refresh.access_token)}")
        print(f"Refresh Token: {str(refresh)}")
        print("=========================")

        return Response({
            'message': 'Đăng nhập bằng Google thành công',
            'status': status.HTTP_200_OK,
            'data': {
                "is_active": user.is_active,
                "is_banned": user.is_banned,
                "role": role,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            'message': f'Google authentication failed: {str(e)}',
            'status': status.HTTP_401_UNAUTHORIZED
        }, status=status.HTTP_401_UNAUTHORIZED)
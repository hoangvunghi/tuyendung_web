from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model, authenticate
from rest_framework.permissions import IsAuthenticated
import logging
from .serializers import UserSerializer,ForgotPasswordSerializer,ResetPasswordSerializer
from django.core.mail import send_mail
from django.conf import settings
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.contrib.auth.hashers import make_password
from json import dumps, loads
from base.permissions import IsAdminUser
from rest_framework_simplejwt.exceptions import TokenError
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.utils.crypto import get_random_string
from datetime import datetime, timedelta
from .models import UserAccount, Role, UserRole
from profiles.models import UserInfo
from django.utils import timezone
from django.shortcuts import render, redirect
from social_django.utils import psa, load_strategy, load_backend
from social_core.exceptions import MissingBackend, AuthTokenError
import requests
from django.utils.http import urlencode
from django.views import View
from django.urls import reverse
from rest_framework.views import APIView

UserAccount = get_user_model()


def register_function(request, is_recruiter=False):
    data = request.data.copy()
    
    serializer = UserSerializer(data=data)
    if serializer.is_valid():
        user = serializer.save()
        if not is_recruiter:
            _role, created = Role.objects.get_or_create(name='candidate')
            role = "candidate"
        else:
            _role, created = Role.objects.get_or_create(name='employer')
            role = "employer"
        UserRole.objects.create(user=user, role=_role)
        activation_token = get_random_string(64)
        expiry_date = timezone.now() + timedelta(days=3)
        
        user.activation_token = activation_token
        user.activation_token_expiry = expiry_date
        user.save()
        
        # Gửi email kích hoạt
        email_subject = f"Kích hoạt tài khoản {role} của bạn"
        email_message = f"Xin chào {user.username},\n\n"
        email_message += "Cảm ơn bạn đã đăng ký tài khoản trên hệ thống của chúng tôi.\n"
        email_message += f"Vui lòng nhấp vào liên kết sau để kích hoạt tài khoản: {settings.BACKEND_URL}/activate/{activation_token}\n\n"
        email_message += f"Lưu ý: Liên kết này sẽ hết hạn sau 3 ngày ({expiry_date.strftime('%d/%m/%Y %H:%M')}).\n\n"
        email_message += "Sau khi kích hoạt tài khoản, bạn sẽ được hoạt động trên website.\n\n"
        email_message += "Trân trọng,\nĐội ngũ quản trị"
        
        send_mail(
            email_subject,
            email_message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
        
        return Response({
            'message': 'Đăng ký tài khoản thành công. Vui lòng kiểm tra email để kích hoạt tài khoản.',
            'status': status.HTTP_201_CREATED,
            'data': serializer.data
        }, status=status.HTTP_201_CREATED)
    return Response({
        'message': 'Đăng ký thất bại',
        'status': status.HTTP_400_BAD_REQUEST,
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)



@swagger_auto_schema(
    method='post',
    operation_description="Đăng ký tài khoản mới",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['username', 'Email', 'password'],
        properties={
            'username': openapi.Schema(type=openapi.TYPE_STRING, description="Tên đăng nhập"),
            'Email': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_EMAIL, description="Địa chỉ email"),
            'password': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_PASSWORD, description="Mật khẩu"),
            "fullname": openapi.Schema(type=openapi.TYPE_STRING, description="Họ và tên"),
            "gender": openapi.Schema(type=openapi.TYPE_STRING, description="Giới tính")
        }
    ),
    responses={
        201: openapi.Response(
            description="User registered successfully",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'data': openapi.Schema(type=openapi.TYPE_OBJECT)
                }
            )
        ),
        400: openapi.Response(
            description="Registration failed",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'errors': openapi.Schema(type=openapi.TYPE_OBJECT)
                }
            )
        )
    }
)
@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    is_recruiter = request.data.get('role') == 'employer'
    return register_function(request, is_recruiter)

@swagger_auto_schema(
    method='get',
    operation_description="Kích hoạt tài khoản người dùng",
    responses={
        200: openapi.Response(
            description="Account activated successfully",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER)
                }
            )
        ),
        404: openapi.Response(
            description="Invalid activation token",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER)
                }
            )
        )
    }
)
@api_view(['GET'])
@permission_classes([AllowAny])
def activate_account(request, token):
    try:
        user = UserAccount.objects.get(activation_token=token)
        if user.activation_token_expiry and user.activation_token_expiry < timezone.now():
            return Response({
                'message': 'Token kích hoạt đã hết hạn. Vui lòng yêu cầu gửi lại email kích hoạt.',
                'status': status.HTTP_400_BAD_REQUEST,
                'expired': True
            }, status=status.HTTP_400_BAD_REQUEST)
            
        user.is_active = True
        user.is_banned = False
        user.activation_token = None
        user.activation_token_expiry = None
        user.save()
        
        return Response({
            'message': 'Tài khoản đã được kích hoạt thành công. Bây giờ bạn có thể đăng nhập.',
            'status': status.HTTP_200_OK
        }, status=status.HTTP_200_OK)
    except UserAccount.DoesNotExist:
        return Response({
            'message': 'Token kích hoạt không hợp lệ.',
            'status': status.HTTP_404_NOT_FOUND
        }, status=status.HTTP_404_NOT_FOUND)
    
@swagger_auto_schema(
    method='post',
    operation_description="Yêu cầu gửi lại email kích hoạt tài khoản",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['email'],
        properties={
            'email': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_EMAIL, description="Địa chỉ email"),
        }
    ),
    responses={
        200: openapi.Response(
            description="Activation email sent successfully",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER)
                }
            )
        ),
        404: openapi.Response(
            description="User not found",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER)
                }
            )
        ),
        400: openapi.Response(
            description="Account already active",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER)
                }
            )
        )
    }
)
@api_view(['POST'])
@permission_classes([AllowAny])
def resend_activation_email(request):
    email = request.data.get('email')
    
    try:
        user = UserAccount.objects.get(email=email)
        
        # Kiểm tra nếu tài khoản đã kích hoạt
        if user.is_active:
            return Response({
                'message': 'Tài khoản này đã được kích hoạt.',
                'status': status.HTTP_400_BAD_REQUEST
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Tạo token kích hoạt mới
        activation_token = get_random_string(64)
        expiry_date = timezone.now() + timedelta(days=3)
        
        user.activation_token = activation_token
        user.activation_token_expiry = expiry_date
        user.save()
        
        # Gửi email kích hoạt
        email_subject = "Kích hoạt tài khoản của bạn"
        email_message = f"Xin chào {user.username},\n\n"
        email_message += "Bạn đã yêu cầu gửi lại email kích hoạt tài khoản.\n"
        email_message += f"Vui lòng nhấp vào liên kết sau để kích hoạt tài khoản: {settings.BACKEND_URL}/activate/{activation_token}\n\n"
        email_message += f"Lưu ý: Liên kết này sẽ hết hạn sau 3 ngày ({expiry_date.strftime('%d/%m/%Y %H:%M')}).\n\n"
        email_message += "Trân trọng,\nĐội ngũ quản trị"
        
        send_mail(
            email_subject,
            email_message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
        
        return Response({
            'message': 'Email kích hoạt đã được gửi lại thành công. Vui lòng kiểm tra email của bạn.',
            'status': status.HTTP_200_OK
        }, status=status.HTTP_200_OK)
        
    except UserAccount.DoesNotExist:
        return Response({
            'message': 'Không tìm thấy tài khoản với email này.',
            'status': status.HTTP_404_NOT_FOUND
        }, status=status.HTTP_404_NOT_FOUND)

@swagger_auto_schema(
    method='post',
    operation_description="Đăng nhập vào hệ thống",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['username', 'password'],
        properties={
            'username': openapi.Schema(type=openapi.TYPE_STRING, description="Tên đăng nhập"),
            'password': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_PASSWORD, description="Mật khẩu"),
        }
    ),
    responses={
        200: openapi.Response(
            description="Login successful",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'data': openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'refresh': openapi.Schema(type=openapi.TYPE_STRING, description="JWT Refresh token"),
                            'access': openapi.Schema(type=openapi.TYPE_STRING, description="JWT Access token"),
                        }
                    )
                }
            )
        ),
        400: openapi.Response(
            description="Invalid credentials",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER)
                }
            )
        )
    }
)
@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    username = request.data.get('username')
    password = request.data.get('password')
    user = authenticate(username=username, password=password)
    
    if user is None:
        try:
            inactive_user = UserAccount.objects.get(username=username)
            if not inactive_user.is_active:
                return Response({
                    'message': 'Tài khoản chưa được kích hoạt. Vui lòng kiểm tra email để kích hoạt tài khoản.',
                    'status': status.HTTP_401_UNAUTHORIZED
                }, status=status.HTTP_401_UNAUTHORIZED)
            if inactive_user.is_banned:
                return Response({
                    'message': 'Tài khoản đã bị vô hiệu hóa. Vui lòng liên hệ quản trị viên để biết thêm thông tin.',
                    'status': status.HTTP_401_UNAUTHORIZED
                }, status=status.HTTP_401_UNAUTHORIZED)
        except UserAccount.DoesNotExist:
            pass
        
        return Response({
            'message': 'Thông tin đăng nhập không hợp lệ',
            'status': status.HTTP_400_BAD_REQUEST
        }, status=status.HTTP_400_BAD_REQUEST)
    
    refresh = RefreshToken.for_user(user)
    refresh["is_active"]=user.is_active
    refresh["is_banned"]=user.is_banned
    if user.is_superuser:
        role = "admin"
    else:
        role = user.get_role()
    refresh["role"]=role
    return Response({
        'message': 'Đăng nhập thành công',
        'status': status.HTTP_200_OK,
        'data': {
            "is_active": user.is_active,
            "is_banned": user.is_banned,
            "role": role,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }
    }, status=status.HTTP_200_OK)

@swagger_auto_schema(
    method='post',
    operation_description="Làm mới token truy cập",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['refresh'],
        properties={
            'refresh': openapi.Schema(type=openapi.TYPE_STRING, description="JWT Refresh token"),
        }
    ),
    responses={
        200: openapi.Response(
            description="Token refreshed successfully",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'data': openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'access': openapi.Schema(type=openapi.TYPE_STRING, description="JWT Access token mới"),
                        }
                    )
                }
            )
        ),
        400: openapi.Response(
            description="Refresh token is required",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER)
                }
            )
        )
    }
)
@api_view(['POST'])
@permission_classes([AllowAny])
def token_refresh(request):
    refresh = request.data.get('refresh')
    if refresh:
        refresh_token = RefreshToken(refresh)
        user_id=refresh_token.payload.get('user_id')
        user=UserAccount.objects.get(id=user_id)
        refresh_token["is_active"]=user.is_active
        if user.is_superuser:
            role = "admin"
        else:
            role = user.get_role()
        refresh_token["role"]=role
        return Response({
            'message': 'Token refreshed successfully',
            'status': status.HTTP_200_OK,
            'data': {
                'access': str(refresh_token.access_token),
            }
        }, status=status.HTTP_200_OK)
    return Response({
        'message': 'Refresh token is required',
        'status': status.HTTP_400_BAD_REQUEST
    }, status=status.HTTP_400_BAD_REQUEST)

@swagger_auto_schema(
    method='post',
    operation_description="Yêu cầu đặt lại mật khẩu",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['email'],
        properties={
            'email': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_EMAIL, description="Địa chỉ email"),
        }
    ),
    responses={
        200: openapi.Response(
            description="Password reset email sent successfully",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER)
                }
            )
        ),
        404: openapi.Response(
            description="UserAccount not found for the provided User",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING)
                }
            )
        ),
        500: openapi.Response(
            description="Failed to generate reset token",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'error': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER)
                }
            )
        )
    }
)
@api_view(["POST"])
@permission_classes([AllowAny])
def forgot_password_view(request):
    serializer = ForgotPasswordSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    email = serializer.validated_data['email']
    try:
        user_account = UserAccount.objects.get(Email=email)
    except UserAccount.DoesNotExist:
        return Response({"message": "UserAccount not found for the provided User"},
                        status=status.HTTP_404_NOT_FOUND)
    try:
        # refresh = RefreshToken.for_user(user)
        # # reset_token = str(refresh.access_token)
        data={"username":user_account.username}
        token=dumps(data, key=settings.SECURITY_PASSWORD_SALT)

    except TokenError as e:
        return Response({"error": "Failed to generate reset token",
                         "status": status.HTTP_500_INTERNAL_SERVER_ERROR},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    email_subject = "Password Reset Request"
    email_message = f"Here's an email about forgetting the password for account: {user_account.username} \n "
    email_message += f"Click the following link to reset your password: {settings.BACKEND_URL}/forgot/reset-password/{token}"

    send_mail(
        email_subject,
        email_message,
        settings.DEFAULT_FROM_EMAIL,
        [email],
        fail_silently=False,
    )

    return Response({"message": "Password reset email sent successfully",
                     "status": status.HTTP_200_OK},
                    status=status.HTTP_200_OK)

@swagger_auto_schema(
    method='post',
    operation_description="Đặt lại mật khẩu",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['password'],
        properties={
            'password': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_PASSWORD, description="Mật khẩu mới"),
        }
    ),
    responses={
        200: openapi.Response(
            description="Password reset successfully",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER)
                }
            )
        ),
        400: openapi.Response(
            description="Invalid reset token",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'error': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER)
                }
            )
        )
    }
)
@api_view(["POST"])
@permission_classes([AllowAny])
def reset_password_view(request, token):
    serializer = ResetPasswordSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    try:
        username = loads(token,key=settings.SECURITY_PASSWORD_SALT)["username"]
        user = UserAccount.objects.get(username=username)
    except (TypeError, ValueError, OverflowError, UserAccount.DoesNotExist):
        return Response({"error": "Invalid reset token",
                         "status": status.HTTP_400_BAD_REQUEST},
                        status=status.HTTP_400_BAD_REQUEST)
    new_password = serializer.validated_data['password']
    if not new_password:
        raise ValidationError("New password is required")
    hashed_password = make_password(new_password)
    user.password = hashed_password
    user.save()
    refresh = RefreshToken.for_user(user)

    return Response({"message": "Password reset successfully",
                     "status": status.HTTP_200_OK},
                    status=status.HTTP_200_OK)

@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def complete_google_oauth2(request):
    """
    Xử lý callback từ Google OAuth2 khi sử dụng social-auth-app-django.
    Endpoint này được gọi bởi social-auth-app-django sau khi xác thực Google.
    """
    
    # Lấy code từ query params (nếu là GET) hoặc từ request body (nếu là POST)
    code = request.GET.get('code') if request.method == 'GET' else request.data.get('code')
    
    if not code:
        return Response({
            'message': 'Không tìm thấy code trong request',
            'status': status.HTTP_400_BAD_REQUEST
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Xử lý authentication với social-auth-app-django
        backend = 'google-oauth2'
        
        # Gọi hàm do_auth của social-auth-app-django
        @psa('social:complete')
        def authenticate(request, backend):
            return request.backend.do_auth(code)
        
        # Thực hiện xác thực
        user = authenticate(request, backend)
        
        if not user:
            return Response({
                'message': 'Xác thực Google thất bại',
                'status': status.HTTP_401_UNAUTHORIZED
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        if not user.is_active:
            return Response({
                'message': 'Tài khoản chưa được kích hoạt. Vui lòng kiểm tra email để kích hoạt tài khoản.',
                'status': status.HTTP_401_UNAUTHORIZED
            }, status=status.HTTP_401_UNAUTHORIZED)
            
        # Tạo tokens
        refresh = RefreshToken.for_user(user)
        refresh["is_active"] = user.is_active
        role = "admin" if user.is_superuser else user.get_role() if hasattr(user, 'get_role') else 'user'
        refresh["role"] = role
        # Trả về tokens
        return Response({
            'message': 'Đăng nhập với Google thành công',
            'status': status.HTTP_200_OK,
            'data': {
                "is_active": user.is_active,
                "role": role,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'message': f'Lỗi khi xử lý Google OAuth: {str(e)}',
            'status': status.HTTP_500_INTERNAL_SERVER_ERROR
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def google_oauth2_login_callback(request):
    """
    Xử lý callback từ Google OAuth2
    """
    
    try:
        # Lấy code từ request
        code = request.GET.get('code')
        
        if not code:
            return Response({
                'message': 'Không tìm thấy code xác thực',
                'status': status.HTTP_400_BAD_REQUEST
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Lấy access token từ Google
        token_url = 'https://oauth2.googleapis.com/token'
        token_data = {
            'code': code,
            'client_id': settings.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY,
            'client_secret': settings.SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET,
            'redirect_uri': f"{settings.BACKEND_URL}/api/social-token/",
            'grant_type': 'authorization_code'
        }
        token_response = requests.post(token_url, data=token_data)
        
        if token_response.status_code != 200:
            return Response({
                'message': 'Lỗi khi xác thực với Google',
                'status': status.HTTP_400_BAD_REQUEST
            }, status=status.HTTP_400_BAD_REQUEST)
        
        access_token = token_response.json().get('access_token')
        
        # Lấy thông tin người dùng từ Google
        userinfo_url = 'https://www.googleapis.com/oauth2/v2/userinfo'
        headers = {'Authorization': f'Bearer {access_token}'}
        userinfo_response = requests.get(userinfo_url, headers=headers)
        
        if userinfo_response.status_code != 200:
            return Response({
                'message': 'Lỗi khi lấy thông tin người dùng từ Google',
                'status': status.HTTP_400_BAD_REQUEST
            }, status=status.HTTP_400_BAD_REQUEST)
        
        userinfo = userinfo_response.json()
        
        # Tìm hoặc tạo người dùng
        try:
            user = UserAccount.objects.get(email=userinfo.get('email'))
        except ObjectDoesNotExist:
            # Tạo người dùng mới nếu chưa tồn tại
            user = UserAccount.objects.create_user(
                email=userinfo.get('email'),
                username=userinfo.get('email'),  # Sử dụng email làm username
                password="11111121213131",  # Password sẽ không được sử dụng với OAuth
                google_id=userinfo.get('id')  # Lưu Google ID
            )
            
            # Cập nhật thông tin người dùng
            if hasattr(user, 'name') and userinfo.get('name'):
                user.name = userinfo.get('name')
            elif hasattr(user, 'first_name') and userinfo.get('given_name'):
                user.first_name = userinfo.get('given_name')
                
            if hasattr(user, 'last_name') and userinfo.get('family_name'):
                user.last_name = userinfo.get('family_name')
                
            # Đánh dấu là người dùng được xác thực bởi Google
            user.is_active = True
            user.save()
        
        # Tạo tokens
        refresh = RefreshToken.for_user(user)
        refresh["is_active"] = user.is_active
        role = "admin" if user.is_superuser else user.get_role() if hasattr(user, 'get_role') else 'user'
        refresh["role"] = role
        
        # Tạo URL redirect với thông tin token và user
        frontend_url = settings.FRONTEND_URL
        redirect_url = f"{frontend_url}?access_token={str(refresh.access_token)}&refresh_token={str(refresh)}&role={role}&email={user.email}"
        return redirect(redirect_url)
        
    except Exception as e:
        return Response({
            'message': 'Lỗi trong quá trình xử lý',
            'status': status.HTTP_500_INTERNAL_SERVER_ERROR
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([AllowAny])
def social_auth_token(request):
    """
    View để lấy JWT token sau khi đăng nhập thành công với social auth
    """
    code = request.GET.get('code', None)
    if code is None:
        return Response({
            'message': 'Code không được cung cấp',
            'status': status.HTTP_400_BAD_REQUEST
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        # Lấy user từ social auth
        strategy = load_strategy(request)
        backend = load_backend(strategy, 'google-oauth2', redirect_uri=None)
        
        # Xác thực user với code
        user = backend.do_auth(code)
        
        if not user:
            return Response({
                'message': 'Xác thực thất bại',
                'status': status.HTTP_401_UNAUTHORIZED
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Tạo JWT token
        refresh = RefreshToken.for_user(user)
        role = "admin" if user.is_superuser else getattr(user, 'role', 'user')
        
        # Trả về dữ liệu dưới dạng JSON thay vì redirect
        return Response({
            'message': 'Đăng nhập thành công',
            'status': status.HTTP_200_OK,
            'data': {
                'access_token': str(refresh.access_token),
                'refresh_token': str(refresh),
                'role': role,
                'email': user.email
            }
        }, status=status.HTTP_200_OK)
    
    except (MissingBackend, AuthTokenError) as e:
        return Response({
            'message': f'Lỗi xác thực: {str(e)}',
            'status': status.HTTP_400_BAD_REQUEST
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({
            'message': f'Lỗi: {str(e)}',
            'status': status.HTTP_500_INTERNAL_SERVER_ERROR
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@swagger_auto_schema(
    method='post',
    operation_description="Bổ sung thông tin cho người dùng sau khi đăng nhập Google",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['fullname', 'gender', 'role'],
        properties={
            'fullname': openapi.Schema(type=openapi.TYPE_STRING, description="Họ và tên"),
            'gender': openapi.Schema(type=openapi.TYPE_STRING, description="Giới tính"),
            'role': openapi.Schema(type=openapi.TYPE_STRING, description="Vai trò (candidate hoặc employer)"),
        }
    ),
    responses={
        200: openapi.Response(
            description="Thông tin đã được cập nhật thành công",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'data': openapi.Schema(type=openapi.TYPE_OBJECT)
                }
            )
        ),
        400: openapi.Response(
            description="Dữ liệu không hợp lệ",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'errors': openapi.Schema(type=openapi.TYPE_OBJECT)
                }
            )
        )
    }
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def complete_google_profile(request):
    user = request.user
    
    # Kiểm tra xem user có phải đăng nhập bằng Google không
    if not user.google_id:
        return Response({
            'message': 'Tài khoản này không phải đăng nhập bằng Google',
            'status': status.HTTP_400_BAD_REQUEST
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Kiểm tra xem user đã có thông tin chưa
    try:
        user_info = UserInfo.objects.get(user=user)
        return Response({
            'message': 'Tài khoản đã có đầy đủ thông tin',
            'status': status.HTTP_400_BAD_REQUEST
        }, status=status.HTTP_400_BAD_REQUEST)
    except UserInfo.DoesNotExist:
        pass
    
    # Xử lý dữ liệu
    fullname = request.data.get('fullname')
    gender = request.data.get('gender')
    role = request.data.get('role')
    
    if not all([fullname, gender, role]):
        return Response({
            'message': 'Vui lòng điền đầy đủ thông tin',
            'status': status.HTTP_400_BAD_REQUEST
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Tạo thông tin người dùng
    UserInfo.objects.create(
        user=user,
        fullname=fullname,
        gender=gender
    )
    
    # Gán vai trò
    _role, created = Role.objects.get_or_create(name=role)
    UserRole.objects.create(user=user, role=_role)
    
    return Response({
        'message': 'Cập nhật thông tin thành công',
        'status': status.HTTP_200_OK,
        'data': {
            'fullname': fullname,
            'gender': gender,
            'role': role
        }
    }, status=status.HTTP_200_OK)

@permission_classes([AllowAny])
def social_auth_complete_redirect(request):
    """
    Lấy token từ session và redirect về frontend.
    """
    access_token = request.session.get('access_token')
    refresh_token = request.session.get('refresh_token')
    role = request.session.get('user_role')
    email = request.session.get('user_email')

    # Xóa token khỏi session sau khi lấy
    request.session.pop('access_token', None)
    request.session.pop('refresh_token', None)
    request.session.pop('user_role', None)
    request.session.pop('user_email', None)

    if not access_token:
        # Xử lý lỗi nếu không tìm thấy token (có thể redirect về trang lỗi FE)
        frontend_login_error_url = f"{settings.FRONTEND_BASE_URL}/login?error=social_auth_failed"
        return redirect(frontend_login_error_url)
    
    # Redirect về frontend kèm theo token
    query_params = urlencode({
        'access_token': access_token,
        'refresh_token': refresh_token,
        'role': role,
        'email': email,
    })
    frontend_complete_url = f"{settings.FRONTEND_BASE_URL}/auth/social/complete?{query_params}"
    
    return redirect(frontend_complete_url)

class FinalizeGoogleAuthView(View):
    def get(self, request, *args, **kwargs):
        # Lấy dữ liệu từ session (được lưu bởi pipeline)
        access_token = request.session.pop('access_token', None)
        refresh_token = request.session.pop('refresh_token', None)
        role = request.session.pop('user_role', None)
        email = request.session.pop('user_email', None)
        is_active = request.session.get('is_active', True)
        is_banned = request.session.get('is_banned', False)

        frontend_callback_url = 'http://localhost:5173/auth/google/callback' # URL callback của frontend

        if access_token and refresh_token and role:
            query_params = urlencode({
                'access_token': access_token,
                'refresh_token': refresh_token,
                'role': role,
                'email': email or '',
                'is_active': str(is_active).lower(),
                'is_banned': str(is_banned).lower()
            })
            # Redirect về frontend với token trong query params
            return redirect(f'{frontend_callback_url}?{query_params}')
        else:
            # Xử lý lỗi nếu không có token
            error_params = urlencode({'error': 'authentication_failed'})
            return redirect(f'{frontend_callback_url}?{error_params}')

# set role for user 
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def set_role_for_user(request):
    user = request.user
    if user.get_role() == 'none':
        role = request.data.get('role')
        UserRole.objects.create(user=user, role=role)
        return Response({
            'message': 'Cập nhật vai trò thành công',
            'data': {
                'role': role,
                'user': user.id
            },
            'status': status.HTTP_200_OK
        })
    else:
        return Response({
            'message': 'Người dùng đã có vai trò',
            'data': {
                'role': user.get_role(),
                'user': user.id
            },
            'status': status.HTTP_400_BAD_REQUEST
        })

import logging
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
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

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
        
        # Sử dụng Celery task để gửi email
        from .tasks import send_activation_email
        send_activation_email.delay(user.username, user.email, activation_token, expiry_date, role)
        
        return Response({
            'message': 'Đăng ký tài khoản thành công. Vui lòng kiểm tra email để kích hoạt tài khoản.',
            'status': status.HTTP_201_CREATED,
            'data': serializer.data
        }, status=status.HTTP_201_CREATED)
    
    # Cải thiện thông báo lỗi để frontend có thể hiển thị chi tiết
    error_messages = {}
    for field, errors in serializer.errors.items():
        error_messages[field] = [str(error) for error in errors]
    
    return Response({
        'message': 'Đăng ký thất bại',
        'status': status.HTTP_400_BAD_REQUEST,
        'errors': error_messages
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
        
        # Sử dụng Celery task để gửi email
        from .tasks import resend_activation_email_task
        resend_activation_email_task.delay(user.username, user.email, activation_token, expiry_date)
        
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
    
    # Khởi tạo dictionary errors để lưu các lỗi
    errors = {}
    
    # Kiểm tra xem username và password có được cung cấp không
    if not username:
        errors['username'] = ['Vui lòng nhập tên đăng nhập']
    
    if not password:
        errors['password'] = ['Vui lòng nhập mật khẩu']
    
    # Nếu có lỗi thiếu thông tin, trả về ngay
    if errors:
        return Response({
            'message': 'Thông tin đăng nhập không đầy đủ',
            'status': status.HTTP_400_BAD_REQUEST,
            'errors': errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    user = authenticate(username=username, password=password)
    
    if user is None:
        try:
            inactive_user = UserAccount.objects.get(username=username)
            if not inactive_user.is_active:
                errors['account'] = ['Tài khoản chưa được kích hoạt. Vui lòng kiểm tra email để kích hoạt tài khoản.']
                return Response({
                    'message': 'Tài khoản chưa được kích hoạt',
                    'status': status.HTTP_401_UNAUTHORIZED,
                    'errors': errors
                }, status=status.HTTP_401_UNAUTHORIZED)
            if inactive_user.is_banned:
                errors['account'] = ['Tài khoản đã bị vô hiệu hóa. Vui lòng liên hệ quản trị viên để biết thêm thông tin.']
                return Response({
                    'message': 'Tài khoản đã bị vô hiệu hóa',
                    'status': status.HTTP_401_UNAUTHORIZED,
                    'errors': errors
                }, status=status.HTTP_401_UNAUTHORIZED)
            # Nếu tài khoản tồn tại nhưng không đăng nhập được, vấn đề là ở mật khẩu
            errors['password'] = ['Mật khẩu không chính xác']
        except UserAccount.DoesNotExist:
            # Nếu tài khoản không tồn tại
            errors['username'] = ['Tài khoản không tồn tại']
        
        return Response({
            'message': 'Thông tin đăng nhập không hợp lệ',
            'status': status.HTTP_400_BAD_REQUEST,
            'errors': errors
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
    print(request.data)
    serializer = ForgotPasswordSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    email = serializer.validated_data['email']
    try:
        user_account = UserAccount.objects.get(email=email)
    except UserAccount.DoesNotExist:
        return Response({"message": "UserAccount not found for the provided User"},
                        status=status.HTTP_404_NOT_FOUND)
    try:
        serializer_token = URLSafeTimedSerializer(settings.SECRET_KEY)
        data = {"username": user_account.username}
        token = serializer_token.dumps(data, salt=settings.SECURITY_PASSWORD_SALT)
    except Exception as e:
        print(e)
        return Response({"error": "Failed to generate reset token",
                         "status": status.HTTP_500_INTERNAL_SERVER_ERROR},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Sử dụng Celery task để gửi email
    from .tasks import send_password_reset_email
    send_password_reset_email.delay(user_account.username, email, token)

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

    serializer_token = URLSafeTimedSerializer(settings.SECRET_KEY)

    try:
        data = serializer_token.loads(token, salt=settings.SECURITY_PASSWORD_SALT, max_age=3600)
        username = data["username"]
        user = UserAccount.objects.get(username=username)
    except (BadSignature, SignatureExpired, UserAccount.DoesNotExist) as e:
        print(e)
        return Response({"error": "Invalid or expired reset token",
                         "status": status.HTTP_400_BAD_REQUEST},
                        status=status.HTTP_400_BAD_REQUEST)

    new_password = serializer.validated_data['password']
    if not new_password:
        raise ValidationError("New password is required")

    user.password = make_password(new_password)
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
    logging.info("Starting complete_google_oauth2")
    
    # Lấy code từ query params (nếu là GET) hoặc từ request body (nếu là POST)
    code = request.GET.get('code') if request.method == 'GET' else request.data.get('code')
    state = request.GET.get('state') if request.method == 'GET' else request.data.get('state')
    
    if not code:
        logging.error("No code provided in request")
        return Response({
            'message': 'Không tìm thấy code trong request',
            'status': status.HTTP_400_BAD_REQUEST
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Xử lý authentication với social-auth-app-django
        backend = 'google-oauth2'
        
        # Sử dụng load_strategy và load_backend thay vì viết lại authenticate
        strategy = load_strategy(request)
        backend_obj = load_backend(strategy, backend, redirect_uri=None)
        
        # Thực hiện xác thực với social auth backend
        user = backend_obj.do_auth(code, state=state)
        
        if not user:
            logging.error("Authentication failed - no user returned")
            return Response({
                'message': 'Xác thực Google thất bại',
                'status': status.HTTP_401_UNAUTHORIZED
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        if not user.is_active:
            logging.error(f"User {user.email} is not active")
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
        logging.error(f"Error in complete_google_oauth2: {str(e)}", exc_info=True)
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
                username=userinfo.get('email'),  # Sử dụng email đầy đủ làm username
                password="12345678",  # Mật khẩu mặc định là 12345678 (thay vì 11111121213131)
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
def social_auth_error_view(request):
    """
    View hiển thị thông báo lỗi và hướng dẫn người dùng khi xảy ra lỗi trong quá trình xác thực Social
    """
    error_type = request.GET.get('error_type', '')
    error_msg = request.GET.get('error_msg', 'Unknown error')
    redirect_url = f"{settings.FRONTEND_URL}/auth/error?error_type={error_type}&error_msg={error_msg}"
    
    logging.info(f"Social Auth Error: {error_type} - {error_msg}")
    
    # Nếu lỗi là AuthAlreadyAssociated, tự động đăng nhập user
    if error_type == 'AuthAlreadyAssociated':
        try:
            # Lấy email từ query param hoặc session
            email = request.GET.get('email') or request.session.get('auth_already_email') or request.session.get('email')
            user_id = request.session.get('auth_already_user_id')
            
            logging.info(f"AuthAlreadyAssociated details - email: {email}, user_id: {user_id}")
            
            # Tìm user từ ID hoặc email
            user = None
            if user_id:
                try:
                    user = UserAccount.objects.get(id=user_id)
                    logging.info(f"Found user by ID: {user.id}")
                except UserAccount.DoesNotExist:
                    logging.error(f"No user found with ID: {user_id}")
            
            if not user and email:
                try:
                    user = UserAccount.objects.get(email=email)
                    logging.info(f"Found user by email: {user.email}")
                except UserAccount.DoesNotExist:
                    logging.error(f"No user found with email: {email}")
            
            if user:
                # Tạo token cho user
                refresh = RefreshToken.for_user(user)
                refresh["is_active"] = user.is_active
                refresh["is_banned"] = getattr(user, 'is_banned', False)
                role = "admin" if user.is_superuser else user.get_role() if hasattr(user, 'get_role') else 'user'
                refresh["role"] = role
                
                # Tạo URL redirect về frontend với token
                redirect_url = f"{settings.FRONTEND_URL}?access_token={str(refresh.access_token)}&refresh_token={str(refresh)}&role={role}&email={user.email}"
                logging.info(f"Redirecting user to frontend with token: {redirect_url}")
                
                # Xóa dữ liệu khỏi session để tránh lỗi bảo mật
                if 'auth_already_user_id' in request.session:
                    del request.session['auth_already_user_id']
                if 'auth_already_email' in request.session:
                    del request.session['auth_already_email']
                if 'email' in request.session:
                    del request.session['email']
                
                return redirect(redirect_url)
            else:
                logging.error("No user found to handle AuthAlreadyAssociated error")
        except Exception as e:
            logging.error(f"Error handling AuthAlreadyAssociated: {str(e)}", exc_info=True)
    
    logging.info(f"Redirecting to error page: {redirect_url}")
    return redirect(redirect_url)

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

        frontend_callback_url = 'https://tuyendungtlu.site/auth/google/callback' # URL callback của frontend

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

@swagger_auto_schema(
    method='get',
    operation_description="Lấy thông tin người dùng theo ID",
    responses={
        200: openapi.Response(
            description="Lấy thông tin người dùng thành công",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'data': openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'username': openapi.Schema(type=openapi.TYPE_STRING),
                            'email': openapi.Schema(type=openapi.TYPE_STRING),
                            'fullname': openapi.Schema(type=openapi.TYPE_STRING),
                            'avatar': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                            'role': openapi.Schema(type=openapi.TYPE_STRING),
                        }
                    )
                }
            )
        ),
        404: openapi.Response(
            description="Không tìm thấy người dùng",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER)
                }
            )
        )
    },
    security=[{'Bearer': []}]
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_info(request, user_id):
    """Lấy thông tin người dùng theo ID"""
    try:
        user = UserAccount.objects.get(id=user_id)
        
        # Lấy profile nếu có
        profile = None
        try:
            from profiles.models import UserInfo
            profile = UserInfo.objects.filter(user=user).first()
        except Exception as e:
            print(f"Lỗi khi lấy profile: {e}")
        
        # Lấy vai trò
        role = user.get_role()
        
        # Chuẩn bị dữ liệu
        data = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'fullname': user.get_full_name() or user.username,
            'avatar': profile.avatar_url if profile and hasattr(profile, 'avatar_url') else None,
            'role': role
        }
        
        return Response({
            'message': 'User info retrieved successfully',
            'status': status.HTTP_200_OK,
            'data': data
        })
    except UserAccount.DoesNotExist:
        return Response({
            'message': 'User not found',
            'status': status.HTTP_404_NOT_FOUND
        }, status=status.HTTP_404_NOT_FOUND)

@swagger_auto_schema(
    method='post',
    operation_description="Hủy trạng thái Premium của người dùng (tự động hoặc thủ công)",
    responses={
        200: openapi.Response(
            description="Hủy Premium thành công",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER)
                }
            )
        ),
        400: openapi.Response(
            description="Lỗi khi hủy Premium",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER)
                }
            )
        )
    },
    security=[{'Bearer': []}]
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def delete_premium(request):
    """
    API để hủy trạng thái Premium của người dùng (tự động hoặc thủ công)
    """
    try:
        user = request.user
        
        # Kiểm tra người dùng có phải Premium không
        if not user.is_premium:
            return Response({
                'message': 'Người dùng không có gói Premium để hủy',
                'status': status.HTTP_400_BAD_REQUEST
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Import model PremiumHistory
        from transactions.models import PremiumHistory
        
        # Lấy lịch sử Premium đang hoạt động
        active_history = PremiumHistory.objects.filter(
            user=user,
            is_active=True
        ).order_by('-created_at').first()
        
        # Hủy trạng thái Premium
        user.is_premium = False
        user.premium_expiry = None
        user.save()
        
        # Cập nhật lịch sử Premium nếu có
        if active_history:
            active_history.is_active = False
            active_history.is_cancelled = True
            active_history.cancelled_date = timezone.now()
            active_history.save()
        
        return Response({
            'message': 'Đã hủy gói Premium thành công',
            'status': status.HTTP_200_OK
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'message': f'Lỗi khi hủy Premium: {str(e)}',
            'status': status.HTTP_400_BAD_REQUEST
        }, status=status.HTTP_400_BAD_REQUEST)

def get_token_for_frontend(backend, user, response, *args, **kwargs):
    """
    Tạo JWT token và thêm vào session
    """
    if backend.name == 'google-oauth2':
        logging.info("Starting get_token_for_frontend")
        
        # Kiểm tra user có tồn tại không
        if not user:
            logging.error("User is None in get_token_for_frontend")
            return None
            
        try:
            # Kiểm tra email có tồn tại không
            if not hasattr(user, 'email') or not user.email:
                logging.error("User has no email attribute")
                return None
                
            refresh = RefreshToken.for_user(user)
            refresh["is_active"] = user.is_active
            refresh["is_banned"] = user.is_banned
            role = "admin" if user.is_superuser else user.get_role()
            refresh["role"] = role
            
            # Lưu token vào session
            request = kwargs.get('request')
            if request:
                request.session['access_token'] = str(refresh.access_token)
                request.session['refresh_token'] = str(refresh)
                request.session['user_role'] = role
                request.session['user_email'] = user.email
                request.session['is_active'] = user.is_active
                request.session['is_banned'] = user.is_banned
                
            return {
                'access_token': str(refresh.access_token),
                'refresh_token': str(refresh),
                'role': role,
                'email': user.email,
                'is_active': user.is_active,
                'is_banned': user.is_banned
            }
            
        except Exception as e:
            logging.error(f"Error in get_token_for_frontend: {str(e)}")
            return None

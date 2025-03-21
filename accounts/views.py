from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model, authenticate
from .serializers import UserSerializer,ForgotPasswordSerializer,ResetPasswordSerializer
from django.core.mail import send_mail
from django.conf import settings
from django.core.exceptions import ValidationError
from django.contrib.auth.hashers import make_password
from json import dumps, loads
from base.permissions import IsAdminUser
from rest_framework_simplejwt.exceptions import TokenError
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.utils.crypto import get_random_string
from datetime import datetime, timedelta

UserAccount = get_user_model()

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
            'is_recruiter': openapi.Schema(type=openapi.TYPE_BOOLEAN, description="Là nhà tuyển dụng"),
            'is_applicant': openapi.Schema(type=openapi.TYPE_BOOLEAN, description="Là người tìm việc"),
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
    serializer = UserSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        
        # Tạo token kích hoạt
        activation_token = get_random_string(64)
        # Thời gian hết hạn sau 3 ngày
        expiry_date = datetime.now() + timedelta(days=3)
        
        user.activation_token = activation_token
        user.activation_token_expiry = expiry_date
        user.save()
        
        # Gửi email kích hoạt
        email_subject = "Kích hoạt tài khoản của bạn"
        email_message = f"Xin chào {user.username},\n\n"
        email_message += "Cảm ơn bạn đã đăng ký tài khoản trên hệ thống của chúng tôi.\n"
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
            'message': 'User registered successfully. Please check your email to activate your account.',
            'status': status.HTTP_201_CREATED,
            'data': serializer.data
        }, status=status.HTTP_201_CREATED)
    return Response({
        'message': 'Registration failed',
        'status': status.HTTP_400_BAD_REQUEST,
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)

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
        if user.activation_token_expiry and user.activation_token_expiry < datetime.now():
            return Response({
                'message': 'Token kích hoạt đã hết hạn. Vui lòng yêu cầu gửi lại email kích hoạt.',
                'status': status.HTTP_400_BAD_REQUEST,
                'expired': True
            }, status=status.HTTP_400_BAD_REQUEST)
            
        user.is_active = True
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
        expiry_date = datetime.now() + timedelta(days=3)
        
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
        except UserAccount.DoesNotExist:
            pass
        
        return Response({
            'message': 'Thông tin đăng nhập không hợp lệ',
            'status': status.HTTP_400_BAD_REQUEST
        }, status=status.HTTP_400_BAD_REQUEST)
    
    refresh = RefreshToken.for_user(user)
    return Response({
        'message': 'Đăng nhập thành công',
        'status': status.HTTP_200_OK,
        'data': {
            "is_active": user.is_active,
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

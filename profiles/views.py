from django.shortcuts import redirect, render, get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework import status
from .models import UserInfo, Cv,CvView
from transactions.models import PremiumHistory
from .serializers import CvPostSerializer, CvUserSerializer, UserInfoSerializer, CvSerializer, CvStatusSerializer
from base.permissions import IsEnterpriseOwner, IsProfileOwner, IsCvOwner, CanManageCv, AdminAccessPermission
from base.pagination import CustomPagination
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from base.utils import create_permission_class_with_admin_override
from base.aws_utils import get_content_type, upload_to_s3
import os
from django.core.cache import cache
from django.utils.http import urlencode
# from base.services import NotificationService
from transactions.vnpay_service import VnPayService
from django.utils import timezone
from datetime import timedelta
from django.urls import reverse
from django.contrib import messages
from django.conf import settings
from accounts.models import UserAccount
from accounts.tasks import send_premium_confirmation_email

# Tạo các lớp quyền kết hợp với quyền admin
AdminOrProfileOwner = create_permission_class_with_admin_override(IsProfileOwner)
AdminOrCvOwner = create_permission_class_with_admin_override(IsCvOwner)
AdminOrCanManageCv = create_permission_class_with_admin_override(CanManageCv)

# Create your views here.
@swagger_auto_schema(
    method='post',
    operation_description="Tạo thông tin người dùng mới",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['user', 'fullname'],
        properties={
            'user': openapi.Schema(type=openapi.TYPE_INTEGER, description="ID của người dùng"),
            'fullname': openapi.Schema(type=openapi.TYPE_STRING, description="Họ tên đầy đủ"),
            'gender': openapi.Schema(type=openapi.TYPE_STRING, description="Giới tính", enum=['male', 'female', 'other']),
            'balance': openapi.Schema(type=openapi.TYPE_NUMBER, description="Số dư tài khoản"),
            'cv_file': openapi.Schema(type=openapi.TYPE_FILE, description="File CV"),
        }
    ),
    responses={
        201: openapi.Response(
            description="UserInfo created successfully",
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
            description="Bad request",
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
@api_view(["POST"])
@permission_classes([AllowAny])
def create_user_info(request):
    try:
        data = request.data.copy()

        # Handle CV file upload if provided
        if 'cv_file' in request.FILES:
            cv_file = request.FILES['cv_file']
            
            # Get username from user ID
            from accounts.models import UserAccount
            user = UserAccount.objects.get(id=data['user'])
            username = user.username
            
            # Generate unique filename with username
            file_extension = os.path.splitext(cv_file.name)[1]
            new_filename = f"{username}_cv{file_extension}"
            
            # Save temporarily
            temp_path = f"temp_{new_filename}"
            with open(temp_path, 'wb+') as destination:
                for chunk in cv_file.chunks():
                    destination.write(chunk)
            
            try:
                # Upload to S3
                url = upload_to_s3(temp_path, new_filename)
                data['cv_attachments_url'] = url
                
                # Clean up temp file
                os.remove(temp_path)
            except Exception as e:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                return Response({'error': f'Error uploading file: {str(e)}'}, 
                             status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        serializer = UserInfoSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "message": "UserInfo created successfully",
                "status": status.HTTP_201_CREATED,
                "data": serializer.data
            }, status=status.HTTP_201_CREATED)
        return Response({
            "message": "Failed to create UserInfo",
            "status": status.HTTP_400_BAD_REQUEST,
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({
            "message": str(e),
            "status": status.HTTP_500_INTERNAL_SERVER_ERROR
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@swagger_auto_schema(
    method='get',
    operation_description="Lấy thông tin người dùng hiện tại",
    responses={
        200: openapi.Response(
            description="Profile retrieved successfully",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'data': openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'user': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'fullname': openapi.Schema(type=openapi.TYPE_STRING),
                            'gender': openapi.Schema(type=openapi.TYPE_STRING),
                            'balance': openapi.Schema(type=openapi.TYPE_NUMBER),
                            'email': openapi.Schema(type=openapi.TYPE_STRING),
                            'is_premium': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                            'created_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                            'updated_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                        }
                    )
                }
            )
        ),
        404: openapi.Response(
            description="Profile not found",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'detail': openapi.Schema(type=openapi.TYPE_STRING)
                }
            )
        )
    },
    security=[{'Bearer': []}]
)
@api_view(["GET"])
@permission_classes([IsAuthenticated, AdminOrProfileOwner])
def get_profile(request):
    profile = get_object_or_404(UserInfo, user=request.user)
    serializer = UserInfoSerializer(profile)
    email = request.user.email
    is_premium = request.user.is_premium
    data = serializer.data.copy()  
    data['email'] = email
    data['is_premium'] = is_premium
    if is_premium:
        data['premium_expiry'] = request.user.premium_expiry
        data['name_display'] = request.user.get_premium_package_name()
        
        # Thêm thông tin về quyền hạn premium
        premium_package = request.user.get_premium_package()
        if premium_package:
            if request.user.is_employer():
                data['premium_permissions'] = {
                    'max_job_posts': premium_package.max_job_posts,
                    'max_cv_views_per_day': premium_package.max_cv_views_per_day,
                    'can_feature_posts': premium_package.can_feature_posts,
                    'can_view_submitted_cvs': premium_package.can_view_submitted_cvs,  # Khả năng xem số CV đã nộp
                    'can_chat_with_candidates': premium_package.can_chat_with_employers,  # Khả năng nhắn tin với ứng viên
                    'remaining_job_posts': max(0, premium_package.max_job_posts - request.user.post_count),
                    'remaining_cv_views': max(0, premium_package.max_cv_views_per_day - request.user.cv_views_today)
                }
            else:
                data['premium_permissions'] = {
                    'priority_in_search': premium_package.priority_in_search,
                    'daily_job_application_limit': premium_package.daily_job_application_limit,
                    'can_view_job_applications': premium_package.can_view_job_applications,
                    'can_chat_with_employers': premium_package.can_chat_with_employers,  # Khả năng nhắn tin với nhà tuyển dụng
                    'remaining_applications': max(0, premium_package.daily_job_application_limit - request.user.job_applications_today)
                }
    return Response({
        'message': 'Profile retrieved successfully',
        'status': status.HTTP_200_OK,
        'data': data
    })

@swagger_auto_schema(
    method='put',
    operation_description="Cập nhật thông tin người dùng",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'fullname': openapi.Schema(type=openapi.TYPE_STRING, description="Họ tên đầy đủ"),
            'gender': openapi.Schema(type=openapi.TYPE_STRING, description="Giới tính", enum=['male', 'female', 'other']),
            'balance': openapi.Schema(type=openapi.TYPE_NUMBER, description="Số dư tài khoản"),
            'cv_file': openapi.Schema(type=openapi.TYPE_FILE, description="File CV"),
        }
    ),
    responses={
        200: openapi.Response(
            description="UserInfo updated successfully",
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
            description="Bad request",
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
@api_view(['PUT'])
@permission_classes([AdminOrProfileOwner])
def update_profile(request):
    try:
        user_info = UserInfo.objects.get(user=request.user)
        data = request.data.copy()

        # Handle CV file upload if provided
        if 'cv_file' in request.FILES:
            cv_file = request.FILES['cv_file']
            username = request.user.username
            
            # Generate unique filename with username
            file_extension = os.path.splitext(cv_file.name)[1]
            new_filename = f"{username}_cv{file_extension}"
            
            # Save temporarily
            temp_path = f"temp_{new_filename}"
            with open(temp_path, 'wb+') as destination:
                for chunk in cv_file.chunks():
                    destination.write(chunk)
            
            try:
                # Upload to S3
                url = upload_to_s3(temp_path, new_filename)
                data['cv_attachments_url'] = url
                
                # Clean up temp file
                os.remove(temp_path)
            except Exception as e:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                return Response({'error': f'Error uploading file: {str(e)}'}, 
                             status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        serializer = UserInfoSerializer(user_info, data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "message": "Profile updated successfully",
                "status": status.HTTP_200_OK,
                "data": serializer.data
            })
        return Response({
            "message": "Failed to update profile",
            "status": status.HTTP_400_BAD_REQUEST,
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    except UserInfo.DoesNotExist:
        return Response({
            "message": "Profile not found",
            "status": status.HTTP_404_NOT_FOUND
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            "message": str(e),
            "status": status.HTTP_500_INTERNAL_SERVER_ERROR
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# @api_view(["DELETE"])
# @permission_classes([AllowAny])
# def delete_user_info(request, pk):
#     try:
#         user_info = UserInfo.objects.get(pk=pk)
#         user_info.delete()
#         return Response({
#             "message": "UserInfo deleted successfully",
#             "status": status.HTTP_204_NO_CONTENT
#         }, status=status.HTTP_204_NO_CONTENT)
#     except UserInfo.DoesNotExist:
#         return Response({
#             "message": "UserInfo not found",
#             "status": status.HTTP_404_NOT_FOUND
#         }, status=status.HTTP_404_NOT_FOUND)
    
@swagger_auto_schema(
    method='get',
    operation_description="Lấy danh sách CV của người dùng đang đăng nhập",
    manual_parameters=[
        openapi.Parameter(
            'page', openapi.IN_QUERY, 
            description="Số trang", 
            type=openapi.TYPE_INTEGER,
            required=False
        ),
        openapi.Parameter(
            'page_size', openapi.IN_QUERY, 
            description="Số lượng CV mỗi trang", 
            type=openapi.TYPE_INTEGER,
            required=False
        ),
    ],
    responses={
        200: openapi.Response(
            description="CVs retrieved successfully",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'data': openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'links': openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'next': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                                    'previous': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                                }
                            ),
                            'total': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'page': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'total_pages': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'page_size': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'results': openapi.Schema(
                                type=openapi.TYPE_ARRAY,
                                items=openapi.Schema(type=openapi.TYPE_OBJECT)
                            ),
                        }
                    )
                }
            )
        )
    },
    security=[{'Bearer': []}]
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, AdminAccessPermission])
def get_my_cvs(request):
    cvs = Cv.objects.filter(user=request.user)
    paginator = CustomPagination()
    paginated_cvs = paginator.paginate_queryset(cvs, request)
    serializer = CvSerializer(paginated_cvs, many=True)
    return paginator.get_paginated_response(serializer.data)

@swagger_auto_schema(
    method='get',
    operation_description="Lấy chi tiết CV theo ID",
    responses={
        200: openapi.Response(
            description="CV detail retrieved successfully",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'data': openapi.Schema(type=openapi.TYPE_OBJECT)
                }
            )
        ),
        404: openapi.Response(
            description="CV not found",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'detail': openapi.Schema(type=openapi.TYPE_STRING)
                }
            )
        )
    },
    security=[{'Bearer': []}]
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, AdminOrCanManageCv])
def get_cv_detail(request, pk):
    cv = get_object_or_404(Cv, id=pk)
    
    # Kiểm tra nếu là nhà tuyển dụng và không phải chủ CV
    if request.user.is_employer() and cv.user != request.user:
        # Kiểm tra giới hạn xem CV
        if not request.user.can_view_cv():
            return Response({
                'message': 'Bạn đã đạt giới hạn số lượng CV có thể xem trong ngày',
                'status': status.HTTP_400_BAD_REQUEST
            }, status=status.HTTP_400_BAD_REQUEST)
            
        # Ẩn thông tin liên hệ cho người dùng không premium hoặc không có quyền xem
        package = request.user.get_premium_package()
        if not package or not package.can_view_candidate_contacts:
            serializer = CvSerializer(cv)
            data = serializer.data.copy()
            # Ẩn thông tin liên hệ
            data['email'] = "***ẩn***"
            data['phone_number'] = "***ẩn***"
            
            # Tăng số lượng CV đã xem trong ngày
            request.user.cv_views_today += 1
            request.user.last_cv_view_date = timezone.now().date()
            request.user.save(update_fields=['cv_views_today', 'last_cv_view_date'])
            
            return Response({
                'message': 'CV detail retrieved successfully (contacts hidden)',
                'status': status.HTTP_200_OK,
                'data': data
            })
        
        # Tăng số lượng CV đã xem trong ngày
        request.user.cv_views_today += 1
        request.user.last_cv_view_date = timezone.now().date()
        request.user.save(update_fields=['cv_views_today', 'last_cv_view_date'])
    
    serializer = CvSerializer(cv)
    return Response({
        'message': 'CV detail retrieved successfully',
        'status': status.HTTP_200_OK,
        'data': serializer.data
    })

@swagger_auto_schema(
    methods=['post'],
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['post', 'name', 'email', 'phone_number'],
        properties={
            'post': openapi.Schema(type=openapi.TYPE_INTEGER),
            'name': openapi.Schema(type=openapi.TYPE_STRING),
            'email': openapi.Schema(type=openapi.TYPE_STRING),
            'phone_number': openapi.Schema(type=openapi.TYPE_STRING),
            'description': openapi.Schema(type=openapi.TYPE_STRING),
            'cv_file': openapi.Schema(type=openapi.TYPE_FILE),
        }
    ),
    responses={
        201: CvSerializer,
        400: 'Bad Request'
    }
)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_cv(request):
    try:
        # Kiểm tra giới hạn ứng tuyển
        # if not request.user.can_apply_job():
        #     return Response({
        #         'message': 'Bạn đã đạt giới hạn số lượng ứng tuyển trong ngày',
        #         'status': status.HTTP_400_BAD_REQUEST,
        #         'errors': 'Bạn đã đạt giới hạn số lượng ứng tuyển trong ngày'
        #     }, status=status.HTTP_400_BAD_REQUEST)
        
        MAX_CV_PER_DAY = 10
        # lấy gói premium của người dùng
        premium_package = PremiumHistory.objects.filter(user=request.user,is_active=True).order_by('-start_date').first()
        if premium_package:
            MAX_CV_PER_DAY = premium_package.package.daily_job_application_limit
        if Cv.objects.filter(user=request.user,created_at__date=timezone.now().date()).count() >= MAX_CV_PER_DAY:
            return Response({
                'message': 'Bạn đã đạt giới hạn số lượng CV tạo trong ngày',
                'status': status.HTTP_400_BAD_REQUEST,
                'errors': 'Bạn đã đạt giới hạn số lượng CV tạo trong ngày'
            }, status=status.HTTP_400_BAD_REQUEST)

        data = request.data.copy()
        data['user'] = request.user.id
        
        if 'cv' in request.FILES:
            cv_file = request.FILES['cv']
            username = request.user.username
            
            file_extension = os.path.splitext(cv_file.name)[1]
            new_filename = f"{username}_cv_{data['post']}{file_extension}"
            
            temp_path = f"temp_{new_filename}"
            with open(temp_path, 'wb+') as destination:
                for chunk in cv_file.chunks():
                    destination.write(chunk)
            
            try:
                url = upload_to_s3(temp_path, new_filename)
                data['cv_file_url'] = url
                
                os.remove(temp_path)
            except Exception as e:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                return Response({'error': f'Error uploading file: {str(e)}'}, 
                             status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        serializer = CvSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            
            # Cập nhật số lần ứng tuyển trong ngày
            request.user.job_applications_today += 1
            request.user.last_application_date = timezone.now().date()
            request.user.save(update_fields=['job_applications_today', 'last_application_date'])
            
            return Response({
                'message': 'CV created successfully',
                'status': status.HTTP_201_CREATED,
                'data': serializer.data
            }, status=status.HTTP_201_CREATED)
        return Response({
            'message': 'Có lỗi xảy ra khi tạo CV',
            'status': status.HTTP_400_BAD_REQUEST,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
        
    except Exception as e:
        return Response({
            'message': str(e),
            'status': status.HTTP_500_INTERNAL_SERVER_ERROR
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@swagger_auto_schema(
    methods=['put'],
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'name': openapi.Schema(type=openapi.TYPE_STRING),
            'email': openapi.Schema(type=openapi.TYPE_STRING),
            'phone_number': openapi.Schema(type=openapi.TYPE_STRING),
            'description': openapi.Schema(type=openapi.TYPE_STRING),
            'cv_file': openapi.Schema(type=openapi.TYPE_FILE),
        }
    ),
    responses={
        200: CvSerializer,
        404: 'Not Found'
    }
)
@api_view(['PUT'])
@permission_classes([AdminOrCvOwner])
def update_cv(request, pk):
    try:
        cv = Cv.objects.get(pk=pk)
        data = request.data.copy()
        
        # Handle CV file upload if provided
        if 'cv_file' in request.FILES:
            cv_file = request.FILES['cv_file']
            username = request.user.username
            
            # Generate unique filename with username
            file_extension = os.path.splitext(cv_file.name)[1]
            new_filename = f"{username}_cv_{cv.post.id}{file_extension}"
            
            # Save temporarily
            temp_path = f"temp_{new_filename}"
            with open(temp_path, 'wb+') as destination:
                for chunk in cv_file.chunks():
                    destination.write(chunk)
            
            try:
                # Upload to S3
                url = upload_to_s3(temp_path, new_filename)
                data['cv_file_url'] = url
                
                # Clean up temp file
                os.remove(temp_path)
            except Exception as e:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                return Response({'error': f'Error uploading file: {str(e)}'}, 
                             status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        serializer = CvSerializer(cv, data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'CV updated successfully',
                'status': status.HTTP_200_OK,
                'data': serializer.data
            })
        return Response({
            'message': 'Failed to update CV',
            'status': status.HTTP_400_BAD_REQUEST,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    except Cv.DoesNotExist:
        return Response({
            'message': 'CV not found',
            'status': status.HTTP_404_NOT_FOUND
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'message': str(e),
            'status': status.HTTP_500_INTERNAL_SERVER_ERROR
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@swagger_auto_schema(
    method='put',
    operation_description="Cập nhật trạng thái CV",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['status'],
        properties={
            'status': openapi.Schema(
                type=openapi.TYPE_STRING, 
                description="Trạng thái CV",
                enum=['pending', 'approved', 'rejected']
            ),
        }
    ),
    responses={
        200: openapi.Response(
            description="CV status updated successfully",
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
            description="Bad request",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'errors': openapi.Schema(type=openapi.TYPE_OBJECT)
                }
            )
        )
    },
    security=[{'Bearer': []}]
)
@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_cv_status(request, pk):
    """Cập nhật trạng thái CV"""
    cv = get_object_or_404(Cv, pk=pk)
    if cv.post.enterprise != request.user.enterprises.first():
        return Response({
            'message': 'You are not authorized to update this CV',
            'status': status.HTTP_403_FORBIDDEN
        }, status=status.HTTP_403_FORBIDDEN)
    serializer = CvStatusSerializer(cv, data=request.data, partial=True)
    if serializer.is_valid():
        old_status = cv.status
        serializer.save()
        
        # # Gửi thông báo đến user
        # if old_status != cv.status:
        #     NotificationService.create_cv_status_notification(
        #         user=cv.user,
        #         cv=cv,
        #         status=cv.status
        #     )
        
        return Response({
            'message': 'Cập nhật trạng thái CV thành công',
            'status': status.HTTP_200_OK,
            'data': serializer.data
        }, status=status.HTTP_200_OK)
    return Response({
        'message': 'Cập nhật trạng thái CV thất bại',
        'status': status.HTTP_400_BAD_REQUEST,
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)

@swagger_auto_schema(
    method='delete',
    operation_description="Xóa CV",
    responses={
        200: openapi.Response(
            description="CV deleted successfully",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                }
            )
        ),
        404: openapi.Response(
            description="CV not found",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'detail': openapi.Schema(type=openapi.TYPE_STRING)
                }
            )
        )
    },
    security=[{'Bearer': []}]
)
@api_view(["DELETE"])
@permission_classes([IsAuthenticated, AdminOrCvOwner])
def delete_cv(request, pk):
    cv = get_object_or_404(Cv, id=pk, user=request.user)
    cv.delete()
    return Response({
        'message': 'CV deleted successfully',
        'status': status.HTTP_200_OK
    })

@swagger_auto_schema(
    method='put',
    operation_description="Cập nhật ghi chú CV",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'note': openapi.Schema(type=openapi.TYPE_STRING, description="Ghi chú CV")
        }
    ),
    responses={
        200: openapi.Response(
            description="CV note updated successfully",
        ),
        404: openapi.Response(
            description="CV not found",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'detail': openapi.Schema(type=openapi.TYPE_STRING)
                }
            )
        )
    },
    security=[{'Bearer': []}]
)
@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_cv_note(request, pk):
    cv = get_object_or_404(Cv, id=pk)
    cv.note = request.data.get('note')
    cv.save()
    return Response({
        'message': 'CV note updated successfully',
    })

# profiles/views.py
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_cvs(request):
    #Sử dụng cache để lấy danh sách các CV của người dùng
    cache_key = f'user_cvs_{request.user.id}'
    cached_response = cache.get(cache_key)
    if cached_response is not None:
        return Response(cached_response)
    
    cvs = Cv.objects.filter(user=request.user)
    paginator = CustomPagination()
    paginated_cvs = paginator.paginate_queryset(cvs, request)
    serializer = CvUserSerializer(paginated_cvs, many=True)
    cache.set(cache_key, serializer.data, timeout=300)
    return paginator.get_paginated_response(serializer.data)


@api_view(['GET'])
@permission_classes([IsEnterpriseOwner])
def get_post_cvs(request, pk):
    # Tạo cache key dựa trên post ID và tham số phân trang
    params = {
        'post_id': str(pk),
        'page': request.query_params.get('page', '1'),
        'page_size': request.query_params.get('page_size', '10'),
        'sort_by': request.query_params.get('sort_by', '-created_at'),
    }
    cache_key = f'post_{pk}_cvs_{urlencode(params)}'
    
 
    cached_response = cache.get(cache_key)
    if cached_response is not None:
        return Response(cached_response)
    

    cvs = Cv.objects.filter(post=pk).order_by('-created_at')
    paginator = CustomPagination()
    paginated_cvs = paginator.paginate_queryset(cvs, request)
    serializer = CvPostSerializer(paginated_cvs, many=True)

    response_data = paginator.get_paginated_response(serializer.data).data
    cache.set(cache_key, response_data, timeout=300)
    
    return Response(response_data)


@api_view(['POST'])
@permission_classes([IsAuthenticated, AdminAccessPermission])
def mark_cv(request, pk):
    """Đánh dấu CV"""
    cv = get_object_or_404(Cv, pk=pk)
    cv.is_marked = not cv.is_marked
    cv.save()
    return Response({
        'message': 'CV marked successfully',
        'status': status.HTTP_200_OK
    }, status=status.HTTP_200_OK)

@swagger_auto_schema(
    method='post',
    operation_description="Đánh dấu CV",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['mark_type'],
        properties={
            'mark_type': openapi.Schema(
                type=openapi.TYPE_STRING, 
                description="Loại đánh dấu",
                enum=['interested', 'shortlisted', 'rejected']
            ),
            'note': openapi.Schema(
                type=openapi.TYPE_STRING,
                description="Ghi chú"
            ),
        }
    ),
    responses={
        200: openapi.Response(
            description="CV marked successfully",
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
            description="Bad request",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'errors': openapi.Schema(type=openapi.TYPE_OBJECT)
                }
            )
        )
    },
    security=[{'Bearer': []}]
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_cv(request, pk):
    cv = get_object_or_404(Cv, id=pk)
    
    # Mark CV logic would be here
    # Create CvMark object, etc.
    
    # NotificationService.notify_cv_marked(cv, request.data.get('mark_type'))
    
    return Response({
        'message': 'CV marked successfully',
        'status': status.HTTP_200_OK,
        'data': {'cv_id': pk, 'mark_type': request.data.get('mark_type')}
    })

@swagger_auto_schema(
    method='post',
    operation_description="Ghi nhận việc xem CV",
    responses={
        200: openapi.Response(
            description="CV view recorded successfully",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'data': openapi.Schema(type=openapi.TYPE_OBJECT)
                }
            )
        ),
        404: openapi.Response(
            description="CV not found",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'detail': openapi.Schema(type=openapi.TYPE_STRING)
                }
            )
        )
    },
    security=[{'Bearer': []}]
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def view_cv(request, pk):
    cv = get_object_or_404(Cv, id=pk)
    if (cv.is_viewed):
        return Response({
            'message': 'CV already viewed',
            'status': status.HTTP_200_OK
        }, status=status.HTTP_200_OK)
    if cv.post.enterprise != request.user.get_enterprise():
        return Response({
            'message': 'You are not authorized to view this CV',
            'status': status.HTTP_403_FORBIDDEN
        }, status=status.HTTP_403_FORBIDDEN)
    
    # Cập nhật trạng thái CV
    cv.is_viewed = True
    cv.save()
    
    # Tạo bản ghi CvView để kích hoạt signal
    try:
        from enterprises.models import EnterpriseEntity
        enterprise = request.user.get_enterprise()
        
        # Tạo CvView để kích hoạt signal
        CvView.objects.create(
            cv=cv,
            viewer=enterprise
        )
        
        # Ghi log
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Đã tạo CvView cho CV #{pk}, enterprise #{enterprise.id}")
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Lỗi khi tạo CvView: {str(e)}")
    
    return Response({
        'message': 'CV marked as viewed',
        'status': status.HTTP_200_OK,
    })


# api lấy danh sách các CV theo trạng thái trả toàn bộ thông tin chia trạng liệt kê 3 trangj thái pending 
@swagger_auto_schema(
    method='get',
    operation_description="Lấy danh sách CV theo trạng thái của doanh nghiệp",
    manual_parameters=[
        openapi.Parameter(
            'status', 
            openapi.IN_QUERY, 
            description="Trạng thái CV (pending, approved, rejected)", 
            type=openapi.TYPE_STRING,
            required=False
        ),
        openapi.Parameter(
            'is_marked', 
            openapi.IN_QUERY, 
            description="Đánh dấu CV (true, false)", 
            type=openapi.TYPE_BOOLEAN,
        )
    ],
    responses={
        200: openapi.Response(
            description="Danh sách CV theo trạng thái",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'data': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_OBJECT))
                }
            )
        )
    },
    security=[{'Bearer': []}]
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, AdminAccessPermission])
def get_cvs_by_status(request):
    """Lấy danh sách CV theo trạng thái của doanh nghiệp"""
    # Kiểm tra quyền truy cập
    if not request.user.is_enterprise:
        return Response({
            'message': 'Bạn không có quyền xem danh sách CV',
            'status': status.HTTP_403_FORBIDDEN
        }, status=status.HTTP_403_FORBIDDEN)
    
    is_marked = request.query_params.get('is_marked', None)
    if is_marked:
        cvs = Cv.objects.filter(post__enterprise_id=request.user.enterprise.id, is_marked=is_marked)
    else:
        cvs = Cv.objects.filter(post__enterprise_id=request.user.enterprise.id)
    
    status = request.query_params.get('status', None)
    if status:
        cvs = cvs.filter(status=status)

    paginator = CustomPagination()
    paginated_cvs = paginator.paginate_queryset(cvs, request)
    serializer = CvSerializer(paginated_cvs, many=True)

    
    return Response({
        'message': 'Lấy danh sách CV thành công',
        'status': status.HTTP_200_OK,
        'data': serializer.data
    })

@swagger_auto_schema(
    method='get',
    operation_description="Lấy thông tin các gói premium",
    responses={
        200: openapi.Response(
            description="Premium packages retrieved successfully",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'data': openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'user_is_premium': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                            'premium_expiry': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                            'packages': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'name': openapi.Schema(type=openapi.TYPE_STRING),
                                    'price': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'description': openapi.Schema(type=openapi.TYPE_STRING),
                                    'features': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_STRING)),
                                    'duration_days': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'employer_features': openapi.Schema(type=openapi.TYPE_OBJECT),
                                    'candidate_features': openapi.Schema(type=openapi.TYPE_OBJECT)
                                }
                            )),
                            'premium_history': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_OBJECT))
                        }
                    )
                }
            )
        )
    },
    security=[{'Bearer': []}]
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_premium_packages(request):
    # Kiểm tra trạng thái premium của người dùng
    user_is_premium = request.user.is_premium
    premium_expiry = request.user.premium_expiry
    
    # Import các model cần thiết
    from transactions.models import PremiumPackage, PremiumHistory
    from accounts.models import Role
    
    # Lấy role của người dùng
    role_user = request.user.get_role()
    
    # Tìm đối tượng Role tương ứng
    try:
        role_obj = Role.objects.get(name=role_user)
        print("role_obj")
        print(role_obj)
        # Lấy các gói Premium từ database với role tương ứng
        packages = PremiumPackage.objects.filter(is_active=True, role=role_obj).order_by('price')
    except Role.DoesNotExist:
        # Nếu không tìm thấy role, lấy tất cả các gói Premium
        packages = PremiumPackage.objects.filter(is_active=True).order_by('price')
    
    packages_data = []
    
    for package in packages:
        # Chuyển đổi JSONField features thành list
        features_list = package.features if isinstance(package.features, list) else []
        
        packages_data.append({
            'id': package.id,
            'name': package.name,
            'price': int(package.price),  # Chuyển Decimal sang int để JSON serializable
            'description': package.description,
            'features': features_list,
            'duration_days': package.duration_days,
            # Thêm các thông tin về quyền hạn premium
            'employer_features': {
                'max_job_posts': package.max_job_posts,
                'max_cv_views_per_day': package.max_cv_views_per_day,
                'can_feature_posts': package.can_feature_posts,
                'can_view_submitted_cvs': package.can_view_submitted_cvs,  # Khả năng xem số CV đã nộp
                'can_chat_with_candidates': package.can_chat_with_employers  # Khả năng nhắn tin với ứng viên
            },
            'candidate_features': {
                'priority_in_search': package.priority_in_search,
                'daily_job_application_limit': package.daily_job_application_limit,
                'can_view_job_applications': package.can_view_job_applications,
                'can_chat_with_employers': package.can_chat_with_employers  # Khả năng nhắn tin với nhà tuyển dụng
            }
        })
    
    # Nếu không có gói nào trong database, dùng gói mặc định
    if not packages_data:
        packages_data = [
            {
                'id': 1,
                'name': 'Gói Premium Tháng',
                'price': 99000,  
                'description': 'Gói premium 1 tháng với đầy đủ tính năng',
                'features': [
                    'Tìm kiếm nâng cao',
                    'Mở khóa đầy đủ thông tin liên hệ',
                    'Ưu tiên hiển thị hồ sơ',
                    'Hỗ trợ 24/7'
                ],
                'duration_days': 30,
                'employer_features': {
                    'max_job_posts': 10,
                    'max_cv_views_per_day': 5,
                    'can_feature_posts': True,
                    'can_view_submitted_cvs': True,
                    'can_chat_with_candidates': True
                },
                'candidate_features': {
                    'priority_in_search': True,
                    'daily_job_application_limit': 5,
                    'can_view_job_applications': True,
                    'can_chat_with_employers': True
                }
            },
            {
                'id': 2,
                'name': 'Gói Premium Năm',
                'price': 999000,  
                'description': 'Gói premium 1 năm với đầy đủ tính năng, tiết kiệm hơn',
                'features': [
                    'Tất cả tính năng của gói tháng',
                    'Tiết kiệm 16% so với đăng ký hàng tháng',
                    'Không bị gián đoạn dịch vụ',
                    'Ưu tiên hỗ trợ kỹ thuật'
                ],
                'duration_days': 365,
                'employer_features': {
                    'max_job_posts': 20,
                    'max_cv_views_per_day': 10,
                    'can_feature_posts': True,
                    'can_view_submitted_cvs': True,
                    'can_chat_with_candidates': True
                },
                'candidate_features': {
                    'priority_in_search': True,
                    'daily_job_application_limit': 10,
                    'can_view_job_applications': True,
                    'can_chat_with_employers': True
                }
            }
        ]
    
    # Lấy lịch sử Premium của người dùng
    premium_history = []
    try:
        history_items = PremiumHistory.objects.filter(user=request.user).order_by('-created_at')[:5]  # 5 gói gần nhất
        
        for item in history_items:
            premium_history.append({
                'id': item.id,
                'package_name': item.package_name,
                'package_price': int(item.package_price),
                'start_date': item.start_date.strftime('%d/%m/%Y'),
                'end_date': item.end_date.strftime('%d/%m/%Y'),
                'is_active': item.is_active,
                'is_cancelled': item.is_cancelled,
                'cancelled_date': item.cancelled_date.strftime('%d/%m/%Y') if item.cancelled_date else None,
            })
    except Exception as e:
        print(f"Error fetching premium history: {str(e)}")
    
    return Response({
        'message': 'Premium packages retrieved successfully',
        'status': status.HTTP_200_OK,
        'data': {
            'user_is_premium': user_is_premium,
            'premium_expiry': premium_expiry.strftime('%d/%m/%Y %H:%M:%S') if premium_expiry else None,
            'packages': packages_data,
            'premium_history': premium_history
        }
    })

@swagger_auto_schema(
    method='post',
    operation_description="Mua gói premium",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['package_id'],
        properties={
            'package_id': openapi.Schema(type=openapi.TYPE_INTEGER, description="ID của gói premium"),
        }
    ),
    responses={
        200: openapi.Response(
            description="Payment URL created successfully",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'data': openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'payment_url': openapi.Schema(type=openapi.TYPE_STRING),
                        }
                    )
                }
            )
        ),
        400: openapi.Response(
            description="Bad request",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                }
            )
        )
    },
    security=[{'Bearer': []}]
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def purchase_premium(request):
    # Kiểm tra xem người dùng đã là premium chưa
    if request.user.is_premium:
        return Response({
            'message': 'Tài khoản của bạn đã là premium',
            'status': status.HTTP_400_BAD_REQUEST
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Lấy ID gói premium từ request
    package_id = request.data.get('package_id')
    
    if not package_id:
        return Response({
            'message': 'Vui lòng chọn gói Premium',
            'status': status.HTTP_400_BAD_REQUEST
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Import model PremiumPackage
    from transactions.models import PremiumPackage
    
    try:
        # Chuyển đổi package_id sang số nguyên
        package_id = int(package_id)
        
        # Tìm gói Premium trong database
        try:
            package = PremiumPackage.objects.get(id=package_id, is_active=True)
        except PremiumPackage.DoesNotExist:
            return Response({
                'message': 'Gói Premium không tồn tại hoặc không hoạt động',
                'status': status.HTTP_400_BAD_REQUEST
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Tạo URL thanh toán VNPay và truyền thêm package_id
        payment_url = VnPayService.create_payment_url(
            request, 
            int(package.price), 
            request.user.id,
            package.id
        )
        
        return Response({
            'message': 'Tạo URL thanh toán thành công',
            'status': status.HTTP_200_OK,
            'data': {
                'payment_url': payment_url,
                'package': {
                    'id': package.id,
                    'name': package.name,
                    'price': int(package.price)
                }
            }
        })
    except ValueError:
        return Response({
            'message': 'ID gói Premium không hợp lệ',
            'status': status.HTTP_400_BAD_REQUEST
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({
            'message': f'Lỗi khi tạo URL thanh toán: {str(e)}',
            'status': status.HTTP_400_BAD_REQUEST
        }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([AllowAny])
def process_return_premium(request):
    """
    Xử lý kết quả từ VNPay sau khi thanh toán Premium
    """
    from transactions.models import PremiumPackage, PremiumHistory
    from datetime import datetime, timedelta
    from django.utils import timezone
    
    # Xử lý kết quả từ VNPay
    is_success, user_id, package_id = VnPayService.process_return_url(request)
    
    # Tham số để redirect về client
    redirect_status = 'success' if is_success else 'failed'
    redirect_url = f"{settings.FRONTEND_URL}/premium?status={redirect_status}"
    
    if is_success and user_id and package_id:
        try:
            # Lấy thông tin người dùng
            user = UserAccount.objects.get(id=user_id)
            
            # Lấy thông tin gói Premium từ database
            package = None
            try:
                package = PremiumPackage.objects.get(id=package_id)
                package_name = package.name
                package_price = package.price
                duration_days = package.duration_days
            except PremiumPackage.DoesNotExist:
                # Nếu không tìm thấy, dùng thông tin mặc định
                premium_packages = {
                    1: {'name': 'Gói Premium Tháng', 'price': 99000, 'duration_days': 30},
                    2: {'name': 'Gói Premium Năm', 'price': 999000, 'duration_days': 365}
                }
                if package_id in premium_packages:
                    package_info = premium_packages[package_id]
                    package_name = package_info['name']
                    package_price = package_info['price']
                    duration_days = package_info['duration_days']
                else:
                    # Nếu không có package_id trong danh sách mặc định, dùng gói tháng
                    package_name = 'Gói Premium Tháng'
                    package_price = 99000
                    duration_days = 30
            
            # Tính ngày bắt đầu và kết thúc
            start_date = timezone.now()
            end_date = start_date + timedelta(days=duration_days)
            
            # Cập nhật thông tin premium cho người dùng
            user.is_premium = True
            user.premium_expiry = end_date
            user.save()
            
            # Tìm giao dịch VnPay
            from transactions.models import VnPayTransaction
            try:
                # Lấy giao dịch gần nhất của người dùng
                transaction = VnPayTransaction.objects.filter(
                    user=user,
                    transaction_status='00'  # Trạng thái thành công
                ).order_by('-created_at').first()
                
                # Lưu lịch sử premium
                premium_history = PremiumHistory.objects.create(
                    user=user,
                    package=package,  # Có thể None nếu không tìm thấy trong database
                    transaction=transaction,
                    package_name=package_name,
                    package_price=package_price,
                    start_date=start_date,
                    end_date=end_date,
                    is_active=True
                )
                
                # Gửi email thông báo đã kích hoạt premium
                send_premium_confirmation_email.delay(
                    user.username,
                    user.email,
                    package_name,
                    end_date,
                    package_price
                )
                
            except Exception as e:
                print(f"Error creating premium history: {str(e)}")
                # Vẫn tiếp tục xử lý nếu có lỗi
            
            return redirect(redirect_url)
            
        except UserAccount.DoesNotExist:
            # Người dùng không tồn tại
            return redirect(redirect_url)
        except Exception as e:
            # Lỗi khác
            print(f"Error processing premium payment: {str(e)}")
            return redirect(redirect_url)
    
            return redirect(redirect_url)
    
    return redirect(redirect_url)

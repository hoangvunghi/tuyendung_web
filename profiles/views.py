from django.shortcuts import render, get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework import status
from .models import UserInfo, Cv
from .serializers import CvPostSerializer, UserInfoSerializer, CvSerializer, CvStatusSerializer
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
            return Response({
                'message': 'CV created successfully',
                'status': status.HTTP_201_CREATED,
                'data': serializer.data
            }, status=status.HTTP_201_CREATED)
        return Response({
            'message': 'Failed to create CV',
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
    print(request.user)
    cvs = Cv.objects.filter(user=request.user)
    paginator = CustomPagination()
    paginated_cvs = paginator.paginate_queryset(cvs, request)
    serializer = CvSerializer(paginated_cvs, many=True)
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
    if cv.post.enterprise != request.user.enterprise:
        return Response({
            'message': 'You are not authorized to view this CV',
            'status': status.HTTP_403_FORBIDDEN
        }, status=status.HTTP_403_FORBIDDEN)
    cv.is_viewed = True
    cv.save()
    serializer = CvSerializer(cv)
    return Response({
        'message': 'CV view recorded successfully',
        'status': status.HTTP_200_OK,
        'data': serializer.data
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
                            'packages': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'name': openapi.Schema(type=openapi.TYPE_STRING),
                                    'price': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'description': openapi.Schema(type=openapi.TYPE_STRING),
                                    'features': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_STRING)),
                                }
                            ))
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
    
    # Danh sách gói premium cố định
    packages = [
        {
            'id': 1,
            'name': 'Gói Premium Tháng',
            'price': 99000,  # 99.000 VND
            'description': 'Gói premium 1 tháng với đầy đủ tính năng',
            'features': [
                'Tìm kiếm nâng cao',
                'Mở khóa đầy đủ thông tin liên hệ',
                'Ưu tiên hiển thị hồ sơ',
                'Hỗ trợ 24/7'
            ]
        },
        {
            'id': 2,
            'name': 'Gói Premium Năm',
            'price': 999000,  # 999.000 VND
            'description': 'Gói premium 1 năm với đầy đủ tính năng, tiết kiệm hơn',
            'features': [
                'Tất cả tính năng của gói tháng',
                'Tiết kiệm 16% so với đăng ký hàng tháng',
                'Không bị gián đoạn dịch vụ',
                'Ưu tiên hỗ trợ kỹ thuật'
            ]
        }
    ]
    
    return Response({
        'message': 'Premium packages retrieved successfully',
        'status': status.HTTP_200_OK,
        'data': {
            'user_is_premium': user_is_premium,
            'packages': packages
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
    
    # Danh sách gói premium cố định
    packages = {
        1: {'name': 'Gói Premium Tháng', 'price': 99000},
        2: {'name': 'Gói Premium Năm', 'price': 999000}
    }
    
    # Kiểm tra ID gói premium hợp lệ
    if not package_id or int(package_id) not in packages:
        return Response({
            'message': 'Gói premium không hợp lệ',
            'status': status.HTTP_400_BAD_REQUEST
        }, status=status.HTTP_400_BAD_REQUEST)
    
    package_id = int(package_id)
    package = packages[package_id]
    
    try:
        # Tạo URL thanh toán VNPay
        payment_url = VnPayService.create_payment_url(request, package['price'], request.user.id)
        
        return Response({
            'message': 'Tạo URL thanh toán thành công',
            'status': status.HTTP_200_OK,
            'data': {
                'payment_url': payment_url
            }
        })
    except Exception as e:
        return Response({
            'message': str(e),
            'status': status.HTTP_400_BAD_REQUEST
        }, status=status.HTTP_400_BAD_REQUEST)

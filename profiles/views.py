from django.shortcuts import render, get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework import status
from .models import UserInfo, Cv
from .serializers import UserInfoSerializer, CvSerializer
from base.permissions import IsProfileOwner, IsCvOwner, CanManageCv, AdminAccessPermission
from base.pagination import CustomPagination
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from base.utils import create_permission_class_with_admin_override

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
    serializer = UserInfoSerializer(data=request.data)
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
    return Response({
        'message': 'Profile retrieved successfully',
        'status': status.HTTP_200_OK,
        'data': serializer.data
    })

@swagger_auto_schema(
    method='put',
    operation_description="Cập nhật thông tin người dùng",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'fullname': openapi.Schema(type=openapi.TYPE_STRING, description="Họ tên đầy đủ"),
            'gender': openapi.Schema(type=openapi.TYPE_STRING, description="Giới tính", enum=['male', 'female', 'other']),
        }
    ),
    responses={
        200: openapi.Response(
            description="Profile updated successfully",
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
@permission_classes([IsAuthenticated, AdminOrProfileOwner])
def update_profile(request):
    profile = get_object_or_404(UserInfo, user=request.user)
    serializer = UserInfoSerializer(profile, data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response({
            'message': 'Profile updated successfully',
            'status': status.HTTP_200_OK,
            'data': serializer.data
        })
    return Response({
        'message': 'Profile update failed',
        'status': status.HTTP_400_BAD_REQUEST,
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)

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
    method='post',
    operation_description="Tạo CV mới",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['post', 'name', 'email', 'phone_number', 'cv_file'],
        properties={
            'post': openapi.Schema(type=openapi.TYPE_INTEGER, description="ID của bài đăng"),
            'name': openapi.Schema(type=openapi.TYPE_STRING, description="Tên ứng viên"),
            'email': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_EMAIL, description="Email"),
            'phone_number': openapi.Schema(type=openapi.TYPE_STRING, description="Số điện thoại"),
            'description': openapi.Schema(type=openapi.TYPE_STRING, description="Mô tả về ứng viên"),
            'cv_file': openapi.Schema(type=openapi.TYPE_FILE, description="File CV"),
        }
    ),
    responses={
        201: openapi.Response(
            description="CV created successfully",
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
@permission_classes([IsAuthenticated, AdminAccessPermission])
def create_cv(request):
    serializer = CvSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(user=request.user)
        return Response({
            'message': 'CV created successfully',
            'status': status.HTTP_201_CREATED,
            'data': serializer.data
        }, status=status.HTTP_201_CREATED)
    return Response({
        'message': 'CV creation failed',
        'status': status.HTTP_400_BAD_REQUEST,
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)

@swagger_auto_schema(
    method='put',
    operation_description="Cập nhật CV",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'name': openapi.Schema(type=openapi.TYPE_STRING, description="Tên ứng viên"),
            'email': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_EMAIL, description="Email"),
            'phone_number': openapi.Schema(type=openapi.TYPE_STRING, description="Số điện thoại"),
            'description': openapi.Schema(type=openapi.TYPE_STRING, description="Mô tả về ứng viên"),
            'cv_file': openapi.Schema(type=openapi.TYPE_FILE, description="File CV"),
        }
    ),
    responses={
        200: openapi.Response(
            description="CV updated successfully",
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
@permission_classes([IsAuthenticated, AdminOrCvOwner])
def update_cv(request, pk):
    cv = get_object_or_404(Cv, id=pk, user=request.user)
    serializer = CvSerializer(cv, data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response({
            'message': 'CV updated successfully',
            'status': status.HTTP_200_OK,
            'data': serializer.data
        })
    return Response({
        'message': 'CV update failed',
        'status': status.HTTP_400_BAD_REQUEST,
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)

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
@permission_classes([IsAuthenticated, AdminOrCanManageCv])
def update_cv_status(request, pk):
    cv = get_object_or_404(Cv, id=pk)
    old_status = cv.status
    
    # Validate status
    status_choices = ['pending', 'approved', 'rejected']
    if 'status' not in request.data or request.data['status'] not in status_choices:
        return Response({
            'message': 'Invalid status',
            'status': status.HTTP_400_BAD_REQUEST,
            'errors': {'status': f'Status must be one of {", ".join(status_choices)}'}
        }, status=status.HTTP_400_BAD_REQUEST)
    
    cv.status = request.data['status']
    cv.save()
    
    # Notify user about status change
    # No notification implementation in this example
    
    serializer = CvSerializer(cv)
    return Response({
        'message': 'CV status updated successfully',
        'status': status.HTTP_200_OK,
        'data': serializer.data
    })

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

# profiles/views.py
@api_view(['GET'])
@permission_classes([IsAuthenticated, AdminAccessPermission])
def get_user_cvs(request):
    cvs = Cv.objects.filter(user=request.user)
    paginator = CustomPagination()
    paginated_cvs = paginator.paginate_queryset(cvs, request)
    serializer = CvSerializer(paginated_cvs, many=True)
    return paginator.get_paginated_response(serializer.data)

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

@api_view(['POST'])
@permission_classes([IsAuthenticated, AdminAccessPermission])
def view_cv(request, pk):
    """Xem CV"""
    cv = get_object_or_404(Cv, pk=pk)
    cv.is_viewed = True
    cv.save()
    return Response({
        'message': 'CV viewed successfully',
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
    
    # Record view logic would be here
    # Create CvView object or update view count
    
    # NotificationService.notify_cv_viewed(cv)
    
    serializer = CvSerializer(cv)
    return Response({
        'message': 'CV view recorded successfully',
        'status': status.HTTP_200_OK,
        'data': serializer.data
    })

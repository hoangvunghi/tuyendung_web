from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Q
from rest_framework import status
from .models import Interview
from .serializers import InterviewSerializer
from base.pagination import CustomPagination
from base.permissions import IsEnterpriseOwner, AdminAccessPermission
from base.utils import create_permission_class_with_admin_override
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

# Tạo các lớp quyền kết hợp với quyền admin
AdminOrEnterpriseOwner = create_permission_class_with_admin_override(IsEnterpriseOwner)

@swagger_auto_schema(
    method='get',
    operation_description="Lấy danh sách lịch phỏng vấn",
    manual_parameters=[
        openapi.Parameter(
            'status', 
            openapi.IN_QUERY, 
            description="Trạng thái lịch phỏng vấn (pending/confirmed/completed/canceled)", 
            type=openapi.TYPE_STRING,
            required=False
        ),
    ],
    responses={
        200: openapi.Response(
            description="Danh sách lịch phỏng vấn được lấy thành công",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'data': openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(type=openapi.TYPE_OBJECT)
                    )
                }
            )
        )
    },
    security=[{'Bearer': []}]
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, AdminAccessPermission])
def get_interviews(request):
    """Lấy danh sách phỏng vấn"""
    if hasattr(request.user, 'enterprise'):
        # Nếu là nhà tuyển dụng
        interviews = Interview.objects.filter(enterprise=request.user.enterprise)
    else:
        # Nếu là ứng viên
        interviews = Interview.objects.filter(candidate=request.user)
    
    # Lọc theo trạng thái
    status_filter = request.query_params.get('status')
    if status_filter:
        interviews = interviews.filter(status=status_filter)
    
    paginator = CustomPagination()
    paginated_interviews = paginator.paginate_queryset(interviews, request)
    serializer = InterviewSerializer(paginated_interviews, many=True)
    return paginator.get_paginated_response(serializer.data)

@swagger_auto_schema(
    method='post',
    operation_description="Tạo lịch phỏng vấn mới",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['cv', 'interview_date', 'interview_time', 'location'],
        properties={
            'cv': openapi.Schema(type=openapi.TYPE_INTEGER, description="ID của CV"),
            'interview_date': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE, description="Ngày phỏng vấn (YYYY-MM-DD)"),
            'interview_time': openapi.Schema(type=openapi.TYPE_STRING, description="Giờ phỏng vấn (HH:MM)"),
            'location': openapi.Schema(type=openapi.TYPE_STRING, description="Địa điểm phỏng vấn"),
            'notes': openapi.Schema(type=openapi.TYPE_STRING, description="Ghi chú phỏng vấn"),
            'is_online': openapi.Schema(type=openapi.TYPE_BOOLEAN, description="Phỏng vấn trực tuyến"),
            'meeting_link': openapi.Schema(type=openapi.TYPE_STRING, description="Link phỏng vấn trực tuyến"),
        }
    ),
    responses={
        201: openapi.Response(
            description="Lịch phỏng vấn được tạo thành công",
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
            description="Lỗi tạo lịch phỏng vấn",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'errors': openapi.Schema(type=openapi.TYPE_OBJECT)
                }
            )
        ),
        404: openapi.Response(
            description="CV không tồn tại",
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
@permission_classes([IsAuthenticated, AdminAccessPermission])
def create_interview(request):
    """Tạo lịch phỏng vấn mới"""
    serializer = InterviewSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(enterprise=request.user.enterprise)
        return Response({
            'message': 'Interview created successfully',
            'status': status.HTTP_201_CREATED,
            'data': serializer.data
        }, status=status.HTTP_201_CREATED)
    return Response({
        'message': 'Interview creation failed',
        'status': status.HTTP_400_BAD_REQUEST,
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)

# get_interview_detail
@swagger_auto_schema(
    method='get',
    operation_description="Xem chi tiết lịch phỏng vấn",
    responses={
        200: openapi.Response(
            description="Chi tiết lịch phỏng vấn được lấy thành công",
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
            description="Lịch phỏng vấn không tồn tại",
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
@permission_classes([IsAuthenticated, AdminOrEnterpriseOwner])
def get_interview_detail(request, pk):
    """Xem chi tiết lịch phỏng vấn"""
    interview = get_object_or_404(Interview, id=pk)
    if not (request.user.is_staff or 
            interview.enterprise.user == request.user or 
            interview.candidate == request.user):
        return Response({
            'message': 'Permission denied',
            'status': status.HTTP_403_FORBIDDEN
        }, status=status.HTTP_403_FORBIDDEN)
    
    serializer = InterviewSerializer(interview)
    return Response({
        'message': 'Interview detail retrieved successfully',
        'status': status.HTTP_200_OK,
        'data': serializer.data
    })
    
# update_interview
@swagger_auto_schema(
    method='put',
    operation_description="Cập nhật thông tin lịch phỏng vấn",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'interview_date': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE, description="Ngày phỏng vấn (YYYY-MM-DD)"),
            'interview_time': openapi.Schema(type=openapi.TYPE_STRING, description="Giờ phỏng vấn (HH:MM)"),
            'location': openapi.Schema(type=openapi.TYPE_STRING, description="Địa điểm phỏng vấn"),
            'notes': openapi.Schema(type=openapi.TYPE_STRING, description="Ghi chú phỏng vấn"),
            'is_online': openapi.Schema(type=openapi.TYPE_BOOLEAN, description="Phỏng vấn trực tuyến"),
            'meeting_link': openapi.Schema(type=openapi.TYPE_STRING, description="Link phỏng vấn trực tuyến"),
            'status': openapi.Schema(
                type=openapi.TYPE_STRING, 
                description="Trạng thái lịch phỏng vấn",
                enum=['pending', 'confirmed', 'completed', 'canceled']
            ),
        }
    ),
    responses={
        200: openapi.Response(
            description="Cập nhật lịch phỏng vấn thành công",
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
            description="Lỗi cập nhật lịch phỏng vấn",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'errors': openapi.Schema(type=openapi.TYPE_OBJECT)
                }
            )
        ),
        404: openapi.Response(
            description="Lịch phỏng vấn không tồn tại",
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
@permission_classes([IsAuthenticated, AdminOrEnterpriseOwner])
def update_interview(request, pk):
    """Cập nhật lịch phỏng vấn"""
    interview = get_object_or_404(Interview, id=pk, enterprise__user=request.user)
    serializer = InterviewSerializer(interview, data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response({
            'message': 'Interview updated successfully',
            'status': status.HTTP_200_OK,
            'data': serializer.data
        })
    return Response({
        'message': 'Interview update failed',
        'status': status.HTTP_400_BAD_REQUEST,
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)
    
# delete_interview
@swagger_auto_schema(
    method='delete',
    operation_description="Xóa lịch phỏng vấn",
    responses={
        200: openapi.Response(
            description="Xóa lịch phỏng vấn thành công",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER)
                }
            )
        ),
        404: openapi.Response(
            description="Lịch phỏng vấn không tồn tại",
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
@api_view(['DELETE'])
@permission_classes([IsAuthenticated, AdminOrEnterpriseOwner])
def delete_interview(request, pk):
    """Xóa lịch phỏng vấn"""
    interview = get_object_or_404(Interview, id=pk, enterprise__user=request.user)
    interview.delete()
    return Response({
        'message': 'Interview deleted successfully',
        'status': status.HTTP_200_OK
    })

# respond_to_interview
@swagger_auto_schema(
    method='post',
    operation_description="Phản hồi lịch phỏng vấn (xác nhận/từ chối)",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['status'],
        properties={
            'status': openapi.Schema(
                type=openapi.TYPE_STRING, 
                description="Trạng thái lịch phỏng vấn", 
                enum=['confirmed', 'canceled']
            ),
            'cancel_reason': openapi.Schema(
                type=openapi.TYPE_STRING, 
                description="Lý do hủy (chỉ cần khi status là canceled)"
            ),
        }
    ),
    responses={
        200: openapi.Response(
            description="Phản hồi lịch phỏng vấn thành công",
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
            description="Lỗi phản hồi lịch phỏng vấn",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'errors': openapi.Schema(type=openapi.TYPE_OBJECT)
                }
            )
        ),
        404: openapi.Response(
            description="Lịch phỏng vấn không tồn tại",
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
def respond_to_interview(request, pk):
    """Phản hồi lịch phỏng vấn"""
    interview = get_object_or_404(Interview, id=pk, candidate=request.user)
    response = request.data.get('response')
    if response not in ['accepted', 'rejected']:
        return Response({
            'message': 'Invalid response',
            'status': status.HTTP_400_BAD_REQUEST
        }, status=status.HTTP_400_BAD_REQUEST)
    
    interview.status = response
    interview.save()
    
    return Response({
        'message': 'Interview response recorded successfully',
        'status': status.HTTP_200_OK,
        'data': InterviewSerializer(interview).data
    })
    
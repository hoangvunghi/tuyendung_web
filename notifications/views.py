from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from .models import Notification
from .serializers import NotificationSerializer
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from base.pagination import CustomPagination
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from base.permissions import AdminAccessPermission
from base.utils import create_permission_class_with_admin_override

# Tạo các lớp quyền kết hợp với quyền admin
AdminOrNotificationOwner = create_permission_class_with_admin_override(IsAuthenticated)

@swagger_auto_schema(
    method='get',
    operation_description="""
    Lấy danh sách thông báo của người dùng đang đăng nhập.
    Thông báo được sắp xếp theo thời gian tạo giảm dần (mới nhất trước).
    Kết quả được phân trang.
    """,
    manual_parameters=[
        openapi.Parameter(
            'page', openapi.IN_QUERY, 
            description="Số trang", 
            type=openapi.TYPE_INTEGER,
            required=False
        ),
        openapi.Parameter(
            'page_size', openapi.IN_QUERY, 
            description="Số lượng thông báo mỗi trang", 
            type=openapi.TYPE_INTEGER,
            required=False
        ),
    ],
    responses={
        200: openapi.Response(
            description="Successful operation",
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
                                items=openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    properties={
                                        'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                        'notification_type': openapi.Schema(
                                            type=openapi.TYPE_STRING, 
                                            enum=['cv_received', 'cv_viewed', 'cv_status_changed', 'cv_marked', 'interview_invited', 'message_received']
                                        ),
                                        'title': openapi.Schema(type=openapi.TYPE_STRING),
                                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                                        'is_read': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                                        'created_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                                        'content_type': openapi.Schema(type=openapi.TYPE_INTEGER),
                                        'object_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    }
                                )
                            ),
                        }
                    )
                }
            )
        ),
        401: openapi.Response(
            description="Unauthorized access",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'detail': openapi.Schema(type=openapi.TYPE_STRING),
                }
            )
        )
    },
    security=[{'Bearer': []}]
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, AdminOrNotificationOwner])
def get_notifications(request):
    notifications = Notification.objects.filter(recipient=request.user)
    
    paginator = CustomPagination()
    paginated_notifications = paginator.paginate_queryset(notifications, request)
    
    serializer = NotificationSerializer(paginated_notifications, many=True)
    return paginator.get_paginated_response(serializer.data)

@swagger_auto_schema(
    method='post',
    operation_description="""
    Đánh dấu một thông báo là đã đọc.
    Người dùng chỉ có thể đánh dấu đã đọc cho các thông báo của chính mình.
    """,
    responses={
        200: openapi.Response(
            description="Successful operation",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(
                        type=openapi.TYPE_STRING,
                        example="Đã đánh dấu là đã đọc"
                    ),
                }
            )
        ),
        404: openapi.Response(
            description="Notification not found",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'detail': openapi.Schema(type=openapi.TYPE_STRING),
                }
            )
        ),
        401: openapi.Response(
            description="Unauthorized access",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'detail': openapi.Schema(type=openapi.TYPE_STRING),
                }
            )
        )
    },
    security=[{'Bearer': []}]
)
@api_view(['POST'])
@permission_classes([IsAuthenticated, AdminOrNotificationOwner])
def mark_as_read(request, notification_id):
    notification = get_object_or_404(
        Notification, 
        id=notification_id,
        recipient=request.user
    )
    notification.is_read = True
    notification.save()
    return Response({'message': 'Đã đánh dấu là đã đọc'})

@swagger_auto_schema(
    method='get',
    operation_description="""
    Lấy số lượng thông báo chưa đọc của người dùng đang đăng nhập.
    Hữu ích cho việc hiển thị badge thông báo.
    """,
    responses={
        200: openapi.Response(
            description="Successful operation",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'unread_count': openapi.Schema(
                        type=openapi.TYPE_INTEGER,
                        description="Số lượng thông báo chưa đọc"
                    ),
                }
            )
        ),
        401: openapi.Response(
            description="Unauthorized access",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'detail': openapi.Schema(type=openapi.TYPE_STRING),
                }
            )
        )
    },
    security=[{'Bearer': []}]
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, AdminOrNotificationOwner])
def get_unread_count(request):
    count = Notification.objects.filter(
        recipient=request.user,
        is_read=False
    ).count()
    return Response({'unread_count': count})
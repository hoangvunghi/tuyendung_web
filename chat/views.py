from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Q, Max, Subquery, OuterRef
from rest_framework import status
from .models import Message
from .serializers import MessageSerializer
from base.pagination import CustomPagination
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from base.permissions import AdminAccessPermission
from rest_framework.permissions import OR
from django.db.models.functions import Greatest

@swagger_auto_schema(
    method='get',
    operation_description="Lấy tin nhắn của cuộc trò chuyện",
    manual_parameters=[
        openapi.Parameter(
            'user_id', 
            openapi.IN_QUERY, 
            description="ID của người dùng trong cuộc trò chuyện", 
            type=openapi.TYPE_INTEGER,
            required=True
        ),
        openapi.Parameter(
            'page', 
            openapi.IN_QUERY, 
            description="Số trang", 
            type=openapi.TYPE_INTEGER,
            required=False
        ),
        openapi.Parameter(
            'page_size', 
            openapi.IN_QUERY, 
            description="Số lượng tin nhắn mỗi trang", 
            type=openapi.TYPE_INTEGER,
            required=False
        ),
        openapi.Parameter(
            'order', 
            openapi.IN_QUERY, 
            description="Thứ tự sắp xếp tin nhắn: 'asc' (cũ đến mới) hoặc 'desc' (mới đến cũ)", 
            type=openapi.TYPE_STRING,
            required=False
        ),
    ],
    responses={
        200: openapi.Response(
            description="Lấy tin nhắn thành công",
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
                                        'sender': openapi.Schema(type=openapi.TYPE_INTEGER),
                                        'recipient': openapi.Schema(type=openapi.TYPE_INTEGER),
                                        'content': openapi.Schema(type=openapi.TYPE_STRING),
                                        'is_read': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                                        'created_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                                    }
                                )
                            ),
                        }
                    )
                }
            )
        ),
        400: openapi.Response(
            description="Thiếu tham số user_id",
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
def get_messages(request):
    """Lấy tin nhắn của cuộc trò chuyện"""
    conversation_with = request.query_params.get('user_id')
    
    if not conversation_with:
        return Response({
            'message': 'user_id parameter is required',
            'status': status.HTTP_400_BAD_REQUEST
        }, status=status.HTTP_400_BAD_REQUEST)
        
    messages = Message.objects.filter(
        Q(sender=request.user, recipient_id=conversation_with) |
        Q(recipient=request.user, sender_id=conversation_with)
    ).order_by('created_at')
    
    paginator = CustomPagination()
    paginated_messages = paginator.paginate_queryset(messages, request)
    serializer = MessageSerializer(paginated_messages, many=True)
    return paginator.get_paginated_response(serializer.data)

@swagger_auto_schema(
    method='post',
    operation_description="Gửi tin nhắn mới",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['recipient', 'content'],
        properties={
            'recipient': openapi.Schema(type=openapi.TYPE_INTEGER, description="ID người nhận tin nhắn"),
            'content': openapi.Schema(type=openapi.TYPE_STRING, description="Nội dung tin nhắn"),
        }
    ),
    responses={
        201: openapi.Response(
            description="Gửi tin nhắn thành công",
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
            description="Lỗi dữ liệu đầu vào",
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
def send_message(request):
    serializer = MessageSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(sender=request.user)
        return Response({
            'message': 'Message sent successfully',
            'status': status.HTTP_201_CREATED,
            'data': serializer.data
        }, status=status.HTTP_201_CREATED)
    return Response({
        'message': 'Message sending failed',
        'status': status.HTTP_400_BAD_REQUEST,
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)

@swagger_auto_schema(
    method='get',
    operation_description="Lấy danh sách tin nhắn chưa đọc",
    manual_parameters=[
        openapi.Parameter(
            'page', 
            openapi.IN_QUERY, 
            description="Số trang", 
            type=openapi.TYPE_INTEGER,
            required=False
        ),
        openapi.Parameter(
            'page_size', 
            openapi.IN_QUERY, 
            description="Số lượng tin nhắn mỗi trang", 
            type=openapi.TYPE_INTEGER,
            required=False
        ),
    ],
    responses={
        200: openapi.Response(
            description="Lấy tin nhắn chưa đọc thành công",
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
@permission_classes([IsAuthenticated])
def get_unread_messages(request):
    """Lấy tin nhắn chưa đọc"""
    messages = Message.objects.filter(recipient=request.user, is_read=False)
    paginator = CustomPagination()
    paginated_messages = paginator.paginate_queryset(messages, request)
    serializer = MessageSerializer(paginated_messages, many=True)
    return paginator.get_paginated_response(serializer.data)

@swagger_auto_schema(
    method='post',
    operation_description="Đánh dấu tin nhắn đã đọc",
    responses={
        200: openapi.Response(
            description="Đánh dấu tin nhắn đã đọc thành công",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER)
                }
            )
        ),
        404: openapi.Response(
            description="Không tìm thấy tin nhắn",
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
def mark_message_read(request, pk):
    """Đánh dấu tin nhắn đã đọc"""
    try:
        message = Message.objects.get(pk=pk)
        message.is_read = True
        message.save()
        return Response({
            'message': 'Message marked as read',
            'status': status.HTTP_200_OK
        }, status=status.HTTP_200_OK)
    except Message.DoesNotExist:
        return Response({
            'message': 'Message not found',
            'status': status.HTTP_404_NOT_FOUND
        }, status=status.HTTP_404_NOT_FOUND)
    
@swagger_auto_schema(
    method='get',
    operation_description="Lấy danh sách cuộc trò chuyện",
    responses={
        200: openapi.Response(
            description="Lấy danh sách cuộc trò chuyện thành công",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'data': openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'sender': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'recipient': openapi.Schema(type=openapi.TYPE_INTEGER)
                            }
                        )
                    )
                }
            )
        )
    },
    security=[{'Bearer': []}]
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_conversations(request):
    """Lấy danh sách cuộc trò chuyện"""
    conversations = Message.objects.filter(
        Q(sender=request.user) | Q(recipient=request.user)
    ).values('sender', 'recipient').distinct()
    return Response({
        'message': 'Conversations retrieved successfully',
        'status': status.HTTP_200_OK,
        'data': conversations
    })

@swagger_auto_schema(
    method='get',
    operation_description="Lấy tin nhắn mới nhất của mỗi cuộc trò chuyện",
    responses={
        200: openapi.Response(
            description="Lấy tin nhắn mới nhất thành công",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'data': openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'sender': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'recipient': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'content': openapi.Schema(type=openapi.TYPE_STRING),
                                'is_read': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                                'created_at': openapi.Schema(type=openapi.TYPE_STRING),
                            }
                        )
                    )
                }
            )
        )
    },
    security=[{'Bearer': []}]
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_latest_messages(request):
    """Lấy tin nhắn mới nhất cho mỗi cuộc trò chuyện"""
    user_id = request.user.id
    
    # Tìm tin nhắn mới nhất cho mỗi cuộc trò chuyện
    latest_messages = []
    
    # Lấy danh sách các cuộc trò chuyện từ tin nhắn
    conversations = Message.objects.filter(
        Q(sender=user_id) | Q(recipient=user_id)
    ).values(
        'sender', 'recipient'
    ).annotate(
        latest_id=Max('id')
    ).order_by('-latest_id')
    
    # Lấy tin nhắn mới nhất từ mỗi cuộc trò chuyện
    for conv in conversations:
        other_user = conv['recipient'] if conv['sender'] == user_id else conv['sender']
        
        # Truy vấn tin nhắn mới nhất giữa người dùng hiện tại và other_user
        latest_message = Message.objects.filter(
            Q(sender=user_id, recipient=other_user) | 
            Q(sender=other_user, recipient=user_id)
        ).order_by('-created_at').first()
        
        if latest_message and latest_message not in latest_messages:
            latest_messages.append(latest_message)
    
    serializer = MessageSerializer(latest_messages, many=True)
    
    return Response({
        'message': 'Latest messages retrieved successfully',
        'status': status.HTTP_200_OK,
        'data': serializer.data
    }, status=status.HTTP_200_OK)

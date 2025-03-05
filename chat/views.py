from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Q
from rest_framework import status
from .models import Message
from .serializers import MessageSerializer
from base.pagination import CustomPagination
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_messages(request):
    """Lấy tin nhắn của cuộc trò chuyện"""
    conversation_with = request.query_params.get('user_id')
    messages = Message.objects.filter(
        Q(sender=request.user, recipient_id=conversation_with) |
        Q(recipient=request.user, sender_id=conversation_with)
    ).order_by('created_at')
    
    paginator = CustomPagination()
    paginated_messages = paginator.paginate_queryset(messages, request)
    serializer = MessageSerializer(paginated_messages, many=True)
    return paginator.get_paginated_response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_message(request):
    """Gửi tin nhắn"""
    serializer = MessageSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(sender=request.user)
        return Response({
            'message': 'Message sent successfully',
            'data': serializer.data
        }, status=201)
    return Response(serializer.errors, status=400)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_messages(request):
    conversation_with = request.query_params.get('user_id')
    messages = Message.objects.filter(
        Q(sender=request.user, recipient_id=conversation_with) |
        Q(recipient=request.user, sender_id=conversation_with)
    ).order_by('created_at')
    
    paginator = CustomPagination()
    paginated_messages = paginator.paginate_queryset(messages, request)
    serializer = MessageSerializer(paginated_messages, many=True)
    return paginator.get_paginated_response(serializer.data)

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

# get_unread_messages
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_unread_messages(request):
    """Lấy tin nhắn chưa đọc"""
    messages = Message.objects.filter(recipient=request.user, is_read=False)
    paginator = CustomPagination()
    paginated_messages = paginator.paginate_queryset(messages, request)
    serializer = MessageSerializer(paginated_messages, many=True)
    return paginator.get_paginated_response(serializer.data)

# mark_message_read
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
    
# get_conversations
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

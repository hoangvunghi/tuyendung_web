from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from .models import Notification
from .serializers import NotificationSerializer
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from base.pagination import CustomPagination

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_notifications(request):
    notifications = Notification.objects.filter(recipient=request.user)
    
    paginator = CustomPagination()
    paginated_notifications = paginator.paginate_queryset(notifications, request)
    
    serializer = NotificationSerializer(paginated_notifications, many=True)
    return paginator.get_paginated_response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_as_read(request, notification_id):
    notification = get_object_or_404(
        Notification, 
        id=notification_id,
        recipient=request.user
    )
    notification.is_read = True
    notification.save()
    return Response({'message': 'Đã đánh dấu là đã đọc'})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_unread_count(request):
    count = Notification.objects.filter(
        recipient=request.user,
        is_read=False
    ).count()
    return Response({'unread_count': count})
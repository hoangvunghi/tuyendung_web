import json
import logging
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.utils import timezone
from .models import Notification

logger = logging.getLogger(__name__)

def send_notification_to_user(user_id, notification_type, title, message, data=None):
    """
    Gửi thông báo realtime tới người dùng qua WebSocket
    
    Args:
        user_id: ID của người dùng nhận thông báo
        notification_type: Loại thông báo ('cv_viewed', 'message', etc.)
        title: Tiêu đề thông báo
        message: Nội dung thông báo
        data: Dữ liệu thêm về thông báo (optional)
    """
    try:
        # Lấy channel layer
        channel_layer = get_channel_layer()
        if not channel_layer:
            logger.error(f"Không thể lấy channel layer")
            return False
        
        # Chuẩn bị dữ liệu thông báo
        notification_data = {
            'type': 'notify',  # Phương thức consumers.py sẽ xử lý
            'data': {
                'type': 'notification',
                'notification_type': notification_type,
                'title': title,
                'message': message,
                'timestamp': timezone.now().isoformat(),
                'data': data or {}
            }
        }
        
        # Gửi thông báo tới group của user
        group_name = f"user_{user_id}"
        logger.info(f"Đang gửi thông báo đến group {group_name}")
        
        # Gọi hàm group_send của channel layer
        async_to_sync(channel_layer.group_send)(
            group_name,
            notification_data
        )
        
        logger.info(f"Đã gửi thông báo realtime tới user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Lỗi khi gửi thông báo realtime: {str(e)}")
        return False

def create_and_send_notification(user, notification_type, title, link, message, related_object=None):
    """
    Tạo thông báo trong cơ sở dữ liệu và gửi thông báo realtime
    
    Args:
        user: Đối tượng User
        notification_type: Loại thông báo
        title: Tiêu đề
        link: Đường dẫn liên kết
        message: Nội dung thông báo
        related_object: Đối tượng liên quan (optional)
    """
    try:
        # 1. Tạo thông báo trong database
        from .services import NotificationService
        notification = NotificationService.create_notification(
            recipient=user,
            notification_type=notification_type,
            title=title,
            link=link,
            message=message,
            related_object=related_object
        )
        
        # 2. Gửi thông báo realtime
        notification_data = {
            'notification_id': notification.id,
            'link': link,
            'created_at': notification.created_at.isoformat()
        }
        
        if related_object:
            # Thêm object_id và content_type nếu có related_object
            notification_data.update({
                'object_id': related_object.id,
                'content_type': related_object._meta.model_name
            })
        
        send_notification_to_user(
            user_id=user.id,
            notification_type=notification_type,
            title=title,
            message=message,
            data=notification_data
        )
        
        return notification
    except Exception as e:
        logger.error(f"Lỗi khi tạo và gửi thông báo: {str(e)}")
        return None 
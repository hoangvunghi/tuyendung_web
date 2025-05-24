from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.db.models import signals
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Notification
from .services import NotificationService
from profiles.models import Cv
from django.contrib.contenttypes.models import ContentType
from model_utils import FieldTracker
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Cv)
def handle_cv_changes(sender, instance, created, **kwargs):
    """Xử lý các thay đổi liên quan đến CV"""
    
    # Trường hợp CV mới được tạo
    if created:
        NotificationService.create_notification(
            recipient=instance.post.enterprise.user,
            notification_type='cv_received',
            title='Có CV mới',
            link=f'/employer/posts/{instance.post.id}',
            message=f'Bạn nhận được CV mới cho vị trí {instance.post.title}',
            related_object=instance
        )
        return

    # Trường hợp trạng thái CV thay đổi
    if instance.tracker.has_changed('status'):
        old_status = instance.tracker.previous('status')
        NotificationService.create_notification(
            recipient=instance.user,
            notification_type='cv_status_changed',
            title='Trạng thái CV đã thay đổi',
            link=f'/job/{instance.post.id}',
            message=f'CV của bạn tới vị trí {instance.post.title} của công ty {instance.post.enterprise.company_name} đã được chuyển từ {NotificationService.translate_status(old_status)} sang {NotificationService.translate_status(instance.status)}',
            related_object=instance
        )

@receiver(signals.pre_save, sender=Cv)
def store_old_status(sender, instance, **kwargs):
    """Lưu trạng thái cũ trước khi cập nhật"""
    if instance.id:
        old_instance = sender.objects.get(id=instance.id)
        instance._old_status = old_instance.status

# Signal cho việc xem CV
@receiver(signals.post_save, sender='profiles.CvView')
def handle_cv_view(sender, instance, created, **kwargs):
    """Xử lý khi CV được xem"""
    if created:
        # Thêm log để debug
        logger.info(f"Signal handle_cv_view được gọi: CvView #{instance.id}, CV #{instance.cv.id}")
        
        # Tạo và gửi thông báo
        title = 'CV của bạn đã được xem'
        message = f'CV của bạn ứng tuyển vị trí {instance.cv.post.title} của công ty {instance.cv.post.enterprise.company_name} đã được xem'
        link = f'/job/{instance.cv.post.id}'
        
        try:
            # Sử dụng hàm utils để vừa tạo thông báo trong database vừa gửi realtime
            create_and_send_notification(
                user=instance.cv.user,
                notification_type='cv_viewed',
                title=title,
                link=link,
                message=message,
                related_object=instance.cv
            )
            logger.info(f"Đã gửi thông báo realtime cho user {instance.cv.user.id} về việc xem CV #{instance.cv.id}")
        except Exception as e:
            logger.error(f"Lỗi khi tạo và gửi thông báo: {str(e)}")
            
            # Vẫn cố gắng tạo thông báo qua NotificationService nếu có lỗi
            NotificationService.create_notification(
                recipient=instance.cv.user,
                notification_type='cv_viewed',
                title=title,
                link=link,
                message=message,
                related_object=instance.cv
            )

# Signal cho việc đánh dấu CV
@receiver(signals.post_save, sender='profiles.CvMark')
def handle_cv_mark(sender, instance, created, **kwargs):
    """Xử lý khi CV được đánh dấu"""
    if created:
        NotificationService.create_notification(
            recipient=instance.cv.user,
            notification_type='cv_marked',
            title='CV của bạn đã được đánh dấu',
            link=f'/job/{instance.cv.post.id}',
            message=f'CV của bạn đã được {instance.marker.enterprise.company_name} đánh dấu {instance.mark_type}',
            related_object=instance.cv
        )

# Signal cho lời mời phỏng vấn
@receiver(signals.post_save, sender='interviews.Interview')
def handle_interview_invitation(sender, instance, created, **kwargs):
    """Xử lý khi có lời mời phỏng vấn"""
    if created:
        NotificationService.create_notification(
            recipient=instance.candidate,
            notification_type='interview_invited',
            title='Lời mời phỏng vấn',
            link=f'/job/{instance.post.id}',
            message=f'Bạn nhận được lời mời phỏng vấn từ {instance.enterprise.company_name}',
            related_object=instance
        )

# Signal cho tin nhắn mới
@receiver(signals.post_save, sender='chat.Message')
def handle_new_message(sender, instance, created, **kwargs):
    """Xử lý khi có tin nhắn mới"""
    if created:
        # Log dữ liệu để debug
        print(f"Tin nhắn mới được tạo: ID={instance.id}, sender={instance.sender.id}, recipient={instance.recipient.id}")
        
        # Lấy tên người gửi an toàn
        try:
            sender_name = instance.sender.get_full_name() or f"Người dùng #{instance.sender.id}"
        except Exception as e:
            sender_name = f"Người dùng #{instance.sender.id}"
            print(f"Lỗi khi lấy tên người gửi: {e}")

        # Tạo notification
        # notification = NotificationService.create_notification(
        #     recipient=instance.recipient,
        #     notification_type='message_received',
        #     title='Tin nhắn mới',
        #     link=f'/messages?user={instance.sender.id}',
        #     message=f'Bạn có tin nhắn mới từ {sender_name}',
        #     related_object=instance
        # )
        
        # Gửi tin nhắn trực tiếp qua WebSocket để đảm bảo realtime
        try:
            channel_layer = get_channel_layer()
            print(f"Gửi tin nhắn qua websocket cho user_{instance.recipient.id}")
            
            # Định dạng thời gian để đảm bảo đúng format ISO
            created_at_iso = instance.created_at.isoformat() if instance.created_at else None
            
            message_data = {
                "type": "new_message",
                "message_id": instance.id,  # Đảm bảo là integer, không phải string
                "sender_id": instance.sender.id,
                "recipient_id": instance.recipient.id,
                "content": instance.content,
                "is_read": instance.is_read,
                "created_at": created_at_iso,
                "sender_name": sender_name
            }
            
            print(f"Dữ liệu tin nhắn WebSocket: {message_data}")
            
            async_to_sync(channel_layer.group_send)(
                f"user_{instance.recipient.id}",
                {
                    "type": "notify",
                    "data": message_data
                }
            )
            print(f"Đã gửi tin nhắn qua websocket thành công")
        except Exception as e:
            print(f"Lỗi khi gửi tin nhắn qua websocket: {e}")

def send_notification_to_websocket(notification):
    """Gửi notification qua WebSocket"""
    channel_layer = get_channel_layer()
    
    # Dữ liệu cơ bản của thông báo
    data = {
        "id": notification.id,
        "type": notification.notification_type,
        "title": notification.title,
        "message": notification.message,
        "link": notification.link,
        "is_read": notification.is_read,
        "created_at": notification.created_at.isoformat(),
        "related_object": {
            "type": notification.content_type.model,
            "id": notification.object_id
        }
    }
    
    # Nếu là thông báo tin nhắn mới, thêm thông tin chi tiết
    if notification.notification_type == 'message_received' and notification.content_object:
        message = notification.content_object
        data.update({
            "type": "new_message",
            "message_id": message.id,
            "sender_id": message.sender.id,
            "recipient_id": message.recipient.id,
            "content": message.content,
            "is_read": message.is_read,
            "sender_name": message.sender.get_full_name() or message.sender.username
        })
    
    async_to_sync(channel_layer.group_send)(
        f"user_{notification.recipient.id}",
        {
            "type": "notify",
            "data": data
        }
    )

# Kết nối signal với websocket
@receiver(post_save, sender=Notification)
def notification_created(sender, instance, created, **kwargs):
    """Gửi notification qua WebSocket khi được tạo"""
    if created:
        send_notification_to_websocket(instance)

def translate_status(status):
    if status == 'pending':
        return 'chờ duyệt'
    elif status == 'approved':
        return 'đã duyệt'
    elif status == 'rejected':
        return 'bị từ chối'

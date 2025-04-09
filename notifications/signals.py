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


@receiver(post_save, sender=Cv)
def handle_cv_changes(sender, instance, created, **kwargs):
    """Xử lý các thay đổi liên quan đến CV"""
    
    # Trường hợp CV mới được tạo
    if created:
        NotificationService.create_notification(
            recipient=instance.post.enterprise.user,
            notification_type='cv_received',
            title='Có CV mới',
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
            message=f'CV của bạn đã được chuyển từ {old_status} sang {instance.status}',
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
        NotificationService.create_notification(
            recipient=instance.cv.user,
            notification_type='cv_viewed',
            title='CV của bạn đã được xem',
            message=f'CV của bạn đã được {instance.viewer.enterprise.company_name} xem',
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
            message=f'Bạn nhận được lời mời phỏng vấn từ {instance.enterprise.company_name}',
            related_object=instance
        )

# Signal cho tin nhắn mới
@receiver(signals.post_save, sender='chat.Message')
def handle_new_message(sender, instance, created, **kwargs):
    """Xử lý khi có tin nhắn mới"""
    if created:
        NotificationService.create_notification(
            recipient=instance.recipient,
            notification_type='message_received',
            title='Tin nhắn mới',
            message=f'Bạn có tin nhắn mới từ {instance.sender.get_full_name()}',
            related_object=instance
        )

def send_notification_to_websocket(notification):
    """Gửi notification qua WebSocket"""
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"user_{notification.recipient.id}",
        {
            "type": "notify",
            "data": {
                "id": notification.id,
                "type": notification.notification_type,
                "title": notification.title,
                "message": notification.message,
                "is_read": notification.is_read,
                "created_at": notification.created_at.isoformat(),
                "related_object": {
                    "type": notification.content_type.model,
                    "id": notification.object_id
                }
            }
        }
    )

# Kết nối signal với websocket
@receiver(post_save, sender=Notification)
def notification_created(sender, instance, created, **kwargs):
    """Gửi notification qua WebSocket khi được tạo"""
    if created:
        send_notification_to_websocket(instance)

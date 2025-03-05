# notifications/services.py
from .models import Notification

class NotificationService:
    @staticmethod
    def create_notification(recipient, notification_type, title, message, related_object):
        return Notification.objects.create(
            recipient=recipient,
            notification_type=notification_type,
            title=title,
            message=message,
            content_object=related_object
        )

    @staticmethod
    def notify_cv_viewed(cv):
        NotificationService.create_notification(
            recipient=cv.user,
            notification_type='cv_viewed',
            title='CV của bạn đã được xem',
            message=f'CV của bạn đã được {cv.post.campaign.enterprise.company_name} xem',
            related_object=cv
        )

    @staticmethod
    def notify_cv_status_changed(cv, old_status, new_status):
        NotificationService.create_notification(
            recipient=cv.user,
            notification_type='cv_status_changed',
            title='Trạng thái CV đã thay đổi',
            message=f'CV của bạn đã được chuyển từ {old_status} sang {new_status}',
            related_object=cv
        )
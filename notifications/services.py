# notifications/services.py
from .models import Notification

class NotificationService:
    @staticmethod
    def create_notification(recipient, notification_type, title, link, message, related_object):
        return Notification.objects.create(
            recipient=recipient,
            notification_type=notification_type,
            title=title,
            link=link,
            message=message,
            content_object=related_object
        )

    @staticmethod
    def notify_cv_viewed(cv):
        NotificationService.create_notification(
            recipient=cv.user,
            notification_type='cv_viewed',
            title='CV của bạn đã được xem',
            link=f'/job/{cv.post.id}',
            message=f'CV của bạn Service tới vị trí {cv.post.title} của công ty {cv.post.enterprise.company_name} đã được xem',
            related_object=cv
        )

    @staticmethod
    def notify_cv_status_changed(cv, old_status, new_status):
        NotificationService.create_notification(
            recipient=cv.user,
            notification_type='cv_status_changed',
            title='Trạng thái CV đã thay đổi',
            link=f'/job/{cv.post.id}',
            message=f'CV của bạn Service tới vị trí {cv.post.title} của công ty {cv.post.enterprise.company_name} đã được chuyển sang trạng thái {NotificationService.translate_status(new_status)}',
            related_object=cv
        )
    
    def translate_status(status):
        if status == 'pending':
            return 'Chờ duyệt'
        elif status == 'approved':
            return 'Đã duyệt'
        elif status == 'rejected':
            return 'Đã từ chối'

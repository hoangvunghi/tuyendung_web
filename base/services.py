from django.db import transaction
from notifications.models import Notification
from django.contrib.contenttypes.models import ContentType

class NotificationService:
    @staticmethod
    def create_cv_status_notification(user, cv, status):
        """Tạo thông báo khi trạng thái CV thay đổi"""
        with transaction.atomic():
            # Tạo nội dung thông báo
            status_mapping = {
                'pending': 'đang chờ xử lý',
                'approved': 'đã được duyệt',
                'rejected': 'đã bị từ chối'
            }
            status_text = status_mapping.get(status, status)
            
            content = f"CV của bạn ứng tuyển vào vị trí {cv.post.title} tại {cv.post.enterprise.company_name} {status_text}"
            
            # Tạo thông báo
            notification = Notification.objects.create(
                user=user,
                content=content,
                content_type=ContentType.objects.get_for_model(cv),
                object_id=cv.id,
                notification_type='cv_status_change'
            )
            
            return notification
            
    @staticmethod
    def create_cv_mark_notification(user, cv, mark_type, marked_by):
        """Tạo thông báo khi CV được đánh dấu"""
        with transaction.atomic():
            # Tạo nội dung thông báo
            mark_mapping = {
                'important': 'đã được đánh dấu là quan trọng',
                'potential': 'đã được đánh dấu là tiềm năng',
                'interview': 'đã được chọn để phỏng vấn',
                'reject': 'đã bị từ chối'
            }
            mark_text = mark_mapping.get(mark_type, 'đã được đánh dấu')
            
            content = f"CV của bạn ứng tuyển vào vị trí {cv.post.title} tại {cv.post.enterprise.company_name} {mark_text} bởi {marked_by.username}"
            
            # Tạo thông báo
            notification = Notification.objects.create(
                user=user,
                content=content,
                content_type=ContentType.objects.get_for_model(cv),
                object_id=cv.id,
                notification_type='cv_marked'
            )
            
            return notification 
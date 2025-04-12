from django.db import transaction
from django.contrib.contenttypes.models import ContentType
from notifications.models import Notification

# class NotificationService:
#     @staticmethod
#     def create_cv_status_notification(user, cv, status):
#         """Tạo thông báo khi trạng thái CV thay đổi"""
#         with transaction.atomic():
#             # Tạo nội dung thông báo
#             status_mapping = {
#                 'pending': 'đang chờ xử lý',
#                 'approved': 'đã được duyệt',
#                 'rejected': 'đã bị từ chối'
#             }
#             status_text = status_mapping.get(status, status)
            
#             message = f"CV của bạn ứng tuyển vào vị trí {cv.post.title} tại {cv.post.enterprise.company_name} {status_text}"
#             title = "Trạng thái CV đã thay đổi"
            
#             # Tạo thông báo
#             notification = Notification.objects.create(
#                 recipient=user,
#                 notification_type='cv_status_changed',
#                 title=title,
#                 message=message,
#                 content_type=ContentType.objects.get_for_model(cv),
#                 object_id=cv.id,
#                 link=f'/job/{cv.post.id}'
#             )
            
#             return notification
            
#     @staticmethod
#     def create_cv_mark_notification(user, cv, mark_type, marked_by):
#         """Tạo thông báo khi CV được đánh dấu"""
#         with transaction.atomic():
#             # Tạo nội dung thông báo
#             mark_mapping = {
#                 'important': 'đã được đánh dấu là quan trọng',
#                 'potential': 'đã được đánh dấu là tiềm năng',
#                 'interview': 'đã được chọn để phỏng vấn',
#                 'reject': 'đã bị từ chối'
#             }
#             mark_text = mark_mapping.get(mark_type, 'đã được đánh dấu')
            
#             message = f"CV của bạn ứng tuyển vào vị trí {cv.post.title} tại {cv.post.enterprise.company_name} {mark_text} bởi {marked_by.username}"
#             title = "CV đã được đánh dấu"
            
#             # Tạo thông báo
#             notification = Notification.objects.create(
#                 recipient=user,
#                 notification_type='cv_marked',
#                 title=title,
#                 message=message,
#                 content_type=ContentType.objects.get_for_model(cv),
#                 object_id=cv.id,
#                 link=f'/job/{cv.post.id}'
#             )
            
#             return notification 
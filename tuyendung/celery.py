import os
from celery import Celery

# Thiết lập biến môi trường Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tuyendung.settings')

# Tạo ứng dụng Celery
app = Celery('tuyendung')

# Nạp cấu hình từ settings.py
app.config_from_object('django.conf:settings', namespace='CELERY')

# Tự động tìm và đăng ký các task trong tất cả các ứng dụng Django
app.autodiscover_tasks()

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}') 
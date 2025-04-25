# Hướng dẫn sử dụng Celery trong dự án

## Giới thiệu

Dự án này sử dụng Celery để xử lý các tác vụ bất đồng bộ, chẳng hạn như gửi email. Điều này giúp cải thiện thời gian phản hồi của API và tránh việc người dùng phải chờ đợi trong khi các tác vụ dài hạn đang được xử lý.

## Cài đặt

Đảm bảo bạn đã cài đặt các package cần thiết:

```bash
pip install celery redis
```

## Cấu hình

Celery đã được cấu hình trong dự án với các tệp sau:

- `tuyendung/celery.py`: Cấu hình chính của Celery
- `tuyendung/__init__.py`: Import Celery khi Django khởi động
- `tuyendung/settings.py`: Các thiết lập cho Celery
- `accounts/tasks.py`: Các tác vụ Celery cho ứng dụng accounts

## Chạy Celery Worker

Để chạy Celery worker, mở một terminal mới và chạy lệnh sau từ thư mục gốc của dự án:

```bash
# Windows
celery -A tuyendung worker --pool=solo -l info

# Linux/Mac
celery -A tuyendung worker -l info
```

## Chạy Redis

Trước khi chạy Celery, bạn cần đảm bảo Redis đang chạy:

### Cài đặt Redis

#### Windows:
1. Tải Redis từ https://github.com/microsoftarchive/redis/releases
2. Cài đặt và chạy dịch vụ Redis

#### Linux:
```bash
sudo apt-get install redis-server
```

#### Mac:
```bash
brew install redis
```

### Khởi động Redis:

#### Windows:
Redis sẽ chạy như một dịch vụ Windows sau khi cài đặt. Kiểm tra bằng:
```
redis-cli ping
```

#### Linux/Mac:
```bash
sudo service redis-server start
# hoặc
redis-server
```

## Giám sát Celery

Bạn có thể sử dụng Flower để giám sát các tác vụ Celery:

```bash
pip install flower
celery -A tuyendung flower
```

Sau đó truy cập http://localhost:5555 để xem giao diện giám sát.

## Cấu hình trong .env

Thêm những biến sau vào file .env của bạn:

```
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

## Các tác vụ đã được cấu hình

Các tác vụ sau đã được cấu hình để chạy bất đồng bộ:

1. Gửi email kích hoạt tài khoản khi đăng ký
2. Gửi lại email kích hoạt tài khoản
3. Gửi email đặt lại mật khẩu
4. Gửi email xác nhận khi người dùng mua gói Premium
5. Gửi email thông báo khi gói Premium sắp hết hạn

## Hướng dẫn tạo tác vụ định kỳ

Để tạo tác vụ định kỳ (ví dụ: gửi email thông báo gói Premium sắp hết hạn), bạn có thể sử dụng Celery Beat:

### Cài đặt Celery Beat

Thêm cấu hình Celery Beat vào file `tuyendung/settings.py`:

```python
# Celery Beat Configuration
CELERY_BEAT_SCHEDULE = {
    'check-premium-expiry': {
        'task': 'accounts.tasks.check_premium_expiry',
        'schedule': crontab(hour=7, minute=0),  # Chạy lúc 7 giờ sáng hàng ngày
    },
}
```

### Tạo task cho Celery Beat

Thêm task sau vào file `accounts/tasks.py`:

```python
@shared_task
def check_premium_expiry():
    """
    Task kiểm tra và gửi email cho người dùng có gói Premium sắp hết hạn (còn 3 ngày)
    """
    from accounts.models import UserAccount
    from django.utils import timezone
    
    # Thời gian hiện tại
    now = timezone.now()
    
    # Thời gian hết hạn trong 3 ngày
    expiry_date_start = now + timedelta(days=3)
    expiry_date_end = now + timedelta(days=4)
    
    # Tìm các người dùng có Premium sắp hết hạn trong 3 ngày
    users = UserAccount.objects.filter(
        is_premium=True,
        premium_expiry__gte=expiry_date_start,
        premium_expiry__lt=expiry_date_end
    )
    
    # Lấy thông tin gói Premium và gửi email thông báo
    for user in users:
        try:
            # Lấy thông tin gói Premium từ lịch sử
            from transactions.models import PremiumHistory
            premium_history = PremiumHistory.objects.filter(
                user=user,
                is_active=True
            ).order_by('-created_at').first()
            
            if premium_history:
                # Gửi email thông báo hết hạn
                send_premium_expiration_notice.delay(
                    user.username,
                    user.email,
                    premium_history.package_name,
                    user.premium_expiry
                )
        except Exception as e:
            print(f"Error sending premium expiry notice to {user.email}: {str(e)}")
```

### Chạy Celery Beat

Để chạy Celery Beat, mở một terminal mới và chạy lệnh sau từ thư mục gốc của dự án:

```bash
# Windows
celery -A tuyendung beat -l info

# Linux/Mac
celery -A tuyendung beat -l info
```

Lưu ý: Bạn vẫn cần chạy Celery worker để xử lý các tác vụ được lên lịch. 
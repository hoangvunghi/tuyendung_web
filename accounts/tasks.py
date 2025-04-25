from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from datetime import timedelta
from django.utils import timezone

@shared_task
def send_activation_email(username, email, activation_token, expiry_date, role="candidate"):
    """
    Task gửi email kích hoạt tài khoản
    """
    email_subject = f"Kích hoạt tài khoản {role} của bạn"
    email_message = f"Xin chào {username},\n\n"
    email_message += "Cảm ơn bạn đã đăng ký tài khoản trên hệ thống của chúng tôi.\n"
    email_message += f"Vui lòng nhấp vào liên kết sau để kích hoạt tài khoản: {settings.BACKEND_URL}/activate/{activation_token}\n\n"
    email_message += f"Lưu ý: Liên kết này sẽ hết hạn sau 3 ngày ({expiry_date.strftime('%d/%m/%Y %H:%M')}).\n\n"
    email_message += "Sau khi kích hoạt tài khoản, bạn sẽ được hoạt động trên website.\n\n"
    email_message += "Trân trọng,\nĐội ngũ quản trị"
    
    return send_mail(
        email_subject,
        email_message,
        settings.DEFAULT_FROM_EMAIL,
        [email],
        fail_silently=False,
    )

@shared_task
def send_password_reset_email(username, email, reset_token):
    """
    Task gửi email đặt lại mật khẩu
    """
    email_subject = "Yêu cầu đặt lại mật khẩu"
    email_message = f"Xin chào {username},\n\n"
    email_message += "Chúng tôi đã nhận được yêu cầu đặt lại mật khẩu cho tài khoản của bạn.\n"
    email_message += f"Vui lòng nhấp vào liên kết sau để đặt lại mật khẩu: {settings.FRONTEND_URL}/reset-password/{reset_token}\n\n"
    email_message += "Nếu bạn không yêu cầu đặt lại mật khẩu, vui lòng bỏ qua email này.\n\n"
    email_message += "Trân trọng,\nĐội ngũ quản trị"
    
    return send_mail(
        email_subject,
        email_message,
        settings.DEFAULT_FROM_EMAIL,
        [email],
        fail_silently=False,
    )

@shared_task
def resend_activation_email_task(username, email, activation_token, expiry_date):
    """
    Task gửi lại email kích hoạt tài khoản
    """
    email_subject = "Kích hoạt tài khoản của bạn"
    email_message = f"Xin chào {username},\n\n"
    email_message += "Bạn đã yêu cầu gửi lại email kích hoạt tài khoản.\n"
    email_message += f"Vui lòng nhấp vào liên kết sau để kích hoạt tài khoản: {settings.BACKEND_URL}/activate/{activation_token}\n\n"
    email_message += f"Lưu ý: Liên kết này sẽ hết hạn sau 3 ngày ({expiry_date.strftime('%d/%m/%Y %H:%M')}).\n\n"
    email_message += "Trân trọng,\nĐội ngũ quản trị"
    
    return send_mail(
        email_subject,
        email_message,
        settings.DEFAULT_FROM_EMAIL,
        [email],
        fail_silently=False,
    )

@shared_task
def send_premium_confirmation_email(username, email, premium_package, expiry_date, amount):
    """
    Task gửi email xác nhận khi người dùng mua gói Premium
    """
    email_subject = "Xác nhận kích hoạt gói Premium"
    email_message = f"Xin chào {username},\n\n"
    email_message += f"Cảm ơn bạn đã mua gói Premium {premium_package} trên hệ thống của chúng tôi.\n\n"
    email_message += f"Chi tiết gói Premium:\n"
    email_message += f"- Gói: {premium_package}\n"
    email_message += f"- Số tiền: {amount:,} VNĐ\n"
    email_message += f"- Ngày hết hạn: {expiry_date.strftime('%d/%m/%Y %H:%M')}\n\n"
    email_message += "Từ bây giờ, bạn có thể sử dụng đầy đủ các tính năng Premium trên hệ thống.\n\n"
    email_message += "Nếu bạn có bất kỳ thắc mắc nào, vui lòng liên hệ với chúng tôi qua email hỗ trợ.\n\n"
    email_message += "Trân trọng,\nĐội ngũ quản trị"
    
    return send_mail(
        email_subject,
        email_message,
        settings.DEFAULT_FROM_EMAIL,
        [email],
        fail_silently=False,
    )

@shared_task
def send_premium_expiration_notice(username, email, premium_package, expiry_date):
    """
    Task gửi email thông báo khi gói Premium sắp hết hạn
    """
    email_subject = "Thông báo gói Premium sắp hết hạn"
    email_message = f"Xin chào {username},\n\n"
    email_message += f"Chúng tôi xin thông báo rằng gói Premium {premium_package} của bạn sẽ hết hạn vào {expiry_date.strftime('%d/%m/%Y %H:%M')}.\n\n"
    email_message += "Để tiếp tục sử dụng các tính năng Premium, vui lòng gia hạn gói dịch vụ trước ngày hết hạn.\n\n"
    email_message += f"Bạn có thể dễ dàng gia hạn bằng cách đăng nhập vào tài khoản của mình và truy cập vào phần 'Gói Premium' trong trang cá nhân.\n\n"
    email_message += "Nếu bạn có bất kỳ thắc mắc nào, vui lòng liên hệ với chúng tôi qua email hỗ trợ.\n\n"
    email_message += "Trân trọng,\nĐội ngũ quản trị"
    
    return send_mail(
        email_subject,
        email_message,
        settings.DEFAULT_FROM_EMAIL,
        [email],
        fail_silently=False,
    )

@shared_task
def check_premium_expiry():
    """
    Task kiểm tra và gửi email cho người dùng có gói Premium sắp hết hạn (còn 3 ngày)
    """
    from accounts.models import UserAccount
    
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
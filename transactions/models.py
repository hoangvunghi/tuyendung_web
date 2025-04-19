from django.db import models
from accounts.models import UserAccount

class HistoryMoney(models.Model):
    id = models.AutoField(primary_key=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    balance_after = models.DecimalField(max_digits=10, decimal_places=2)
    is_add_money = models.BooleanField()
    user = models.ForeignKey(UserAccount, on_delete=models.CASCADE, related_name='history_money')
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)  
    
    def __str__(self):
        return f"History for {self.user.username} - Amount: {self.amount}"
    
    class Meta:
        verbose_name = 'Lịch sử giao dịch'
        verbose_name_plural = 'Lịch sử giao dịch'

class VnPayTransaction(models.Model):
    user = models.ForeignKey(UserAccount, on_delete=models.CASCADE, related_name='vnpay_transactions')
    amount = models.IntegerField()  # Số tiền, đơn vị VND
    transaction_no = models.CharField(max_length=255, null=True, blank=True)  # Mã giao dịch từ VNPay
    transaction_status = models.CharField(max_length=255, null=True, blank=True)  # Trạng thái giao dịch
    order_info = models.CharField(max_length=255, null=True, blank=True)  # Thông tin đơn hàng
    txn_ref = models.CharField(max_length=255, null=True, blank=True)  # Mã tham chiếu giao dịch
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"VnPay Transaction for {self.user.username} - Amount: {self.amount}"
    
    class Meta:
        verbose_name = 'Giao dịch VnPay'
        verbose_name_plural = 'Giao dịch VnPay'

class PremiumPackage(models.Model):
    name = models.CharField(max_length=100)  
    description = models.TextField()
    name_display = models.CharField(max_length=100, null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)  # Giá gói Premium
    duration_days = models.IntegerField()  # Thời hạn gói (tính bằng ngày)
    features = models.JSONField(default=list)  # Các tính năng của gói
    is_active = models.BooleanField(default=True)  # Trạng thái hoạt động của gói
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} - {self.price}"
    
    class Meta:
        verbose_name = 'Gói Premium'
        verbose_name_plural = 'Gói Premium'

class PremiumHistory(models.Model):
    user = models.ForeignKey(UserAccount, on_delete=models.CASCADE, related_name='premium_history')
    package = models.ForeignKey(PremiumPackage, on_delete=models.SET_NULL, null=True, related_name='purchase_history')
    transaction = models.ForeignKey(VnPayTransaction, on_delete=models.SET_NULL, null=True, blank=True, related_name='premium_purchases')
    package_name = models.CharField(max_length=100)  # Lưu tên gói để giữ lịch sử ngay cả khi gói bị xóa
    package_price = models.DecimalField(max_digits=10, decimal_places=2)  # Lưu giá gói đã mua
    start_date = models.DateTimeField()  # Ngày bắt đầu gói Premium
    end_date = models.DateTimeField()  # Ngày kết thúc gói Premium
    is_active = models.BooleanField(default=True)  # Trạng thái hoạt động của gói
    is_cancelled = models.BooleanField(default=False)  # Đánh dấu nếu gói bị hủy trước thời hạn
    cancelled_date = models.DateTimeField(null=True, blank=True)  # Ngày hủy gói nếu bị hủy
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Premium for {self.user.username} - {self.package_name} - {self.start_date} to {self.end_date}"
    
    class Meta:
        verbose_name = 'Lịch sử Premium'
        verbose_name_plural = 'Lịch sử Premium'
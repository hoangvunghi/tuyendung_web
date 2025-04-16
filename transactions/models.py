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
import urllib.parse
import hashlib
import hmac
import json
from datetime import datetime
import pytz
from .vnpay_config import VnPayConfig
from .models import VnPayTransaction
from accounts.models import UserAccount

class VnPayService:
    @staticmethod
    def create_payment_url(request, amount, user_id, package_id=None):
        """
        Tạo URL thanh toán VNPay cho người dùng
        
        Args:
            request: HttpRequest object
            amount: Số tiền thanh toán (VND)
            user_id: ID của người dùng
            package_id: ID của gói premium (nếu có)
        
        Returns:
            URL thanh toán VNPay
        """
        # Lấy thông tin cấu hình
        vnp_Version = VnPayConfig.vnp_Version
        vnp_Command = VnPayConfig.vnp_Command
        vnp_TmnCode = VnPayConfig.vnp_TmnCode
        vnp_HashSecret = VnPayConfig.vnp_HashSecret
        
        # Tạo thông tin giao dịch
        vnp_TxnRef = VnPayConfig.get_random_number(8)  # Mã giao dịch, cần đảm bảo unique
        # Thêm thông tin gói premium vào OrderInfo
        if package_id:
            vnp_OrderInfo = f"premium_{user_id}_{package_id}"  # Mô tả đơn hàng với ID gói
        else:
            vnp_OrderInfo = f"premium_{user_id}"  # Mô tả đơn hàng
        vnp_OrderType = "billpayment"
        vnp_Amount = int(amount) * 100  # VNPay yêu cầu số tiền * 100
        vnp_Locale = 'vn'
        vnp_IpAddr = VnPayConfig.get_client_ip(request)
        vnp_ReturnUrl = request.build_absolute_uri('/')[:-1] + VnPayConfig.vnp_ReturnUrl
        
        # Tạo thời gian giao dịch
        vnp_CreateDate = datetime.now(pytz.timezone('Asia/Ho_Chi_Minh')).strftime('%Y%m%d%H%M%S')
        
        # Tạo params
        vnp_Params = {
            'vnp_Version': vnp_Version,
            'vnp_Command': vnp_Command,
            'vnp_TmnCode': vnp_TmnCode,
            'vnp_Amount': str(vnp_Amount),
            'vnp_CurrCode': 'VND',
            'vnp_TxnRef': vnp_TxnRef,
            'vnp_OrderInfo': vnp_OrderInfo,
            'vnp_OrderType': vnp_OrderType,
            'vnp_Locale': vnp_Locale,
            'vnp_ReturnUrl': vnp_ReturnUrl,
            'vnp_IpAddr': vnp_IpAddr,
            'vnp_CreateDate': vnp_CreateDate,
        }
        
        # Sắp xếp params theo key
        sorted_params = sorted(vnp_Params.items())
        hash_data = '&'.join([f"{k}={urllib.parse.quote_plus(str(v))}" for k, v in sorted_params])
        
        # Tạo chữ ký
        secure_hash = VnPayConfig.hmacsha512(vnp_HashSecret, hash_data)
        vnp_Params['vnp_SecureHash'] = secure_hash
        
        # Tạo URL thanh toán
        payment_url = VnPayConfig.vnp_Url + '?' + urllib.parse.urlencode(vnp_Params)
        
        # Lưu giao dịch vào database
        user = UserAccount.objects.get(id=user_id)
        transaction = VnPayTransaction.objects.create(
            user=user,
            amount=int(amount),
            txn_ref=vnp_TxnRef,
            order_info=vnp_OrderInfo
        )
        
        return payment_url
    
    @staticmethod
    def process_return_url(request):
        """
        Xử lý kết quả trả về từ VNPay
        
        Args:
            request: HttpRequest object
        
        Returns:
            Tuple (is_success, user_id, package_id)
        """
        # Lấy các tham số từ request
        input_data = request.GET
        if not input_data:
            return False, None, None
        
        # Tạo danh sách tham số để kiểm tra
        vnp_Params = {}
        for key, value in input_data.items():
            if key.startswith('vnp_'):
                vnp_Params[key] = value
        
        # Kiểm tra chữ ký
        vnp_SecureHash = vnp_Params.pop('vnp_SecureHash', None)
        if not vnp_SecureHash:
            return False, None, None
        
        # Sắp xếp params theo key
        sorted_params = sorted(vnp_Params.items())
        hash_data = '&'.join([f"{k}={urllib.parse.quote_plus(str(v))}" for k, v in sorted_params])
        
        # Tính toán chữ ký
        secure_hash = VnPayConfig.hmacsha512(VnPayConfig.vnp_HashSecret, hash_data)
        
        # So sánh chữ ký
        if secure_hash != vnp_SecureHash:
            return False, None, None
        
        # Lấy thông tin giao dịch
        vnp_ResponseCode = vnp_Params.get('vnp_ResponseCode')
        vnp_TxnRef = vnp_Params.get('vnp_TxnRef')
        vnp_OrderInfo = vnp_Params.get('vnp_OrderInfo')
        vnp_TransactionNo = vnp_Params.get('vnp_TransactionNo')
        
        # Kiểm tra mã giao dịch
        if not vnp_TxnRef:
            return False, None, None
        
        # Tìm giao dịch trong database
        try:
            transaction = VnPayTransaction.objects.get(txn_ref=vnp_TxnRef)
        except VnPayTransaction.DoesNotExist:
            return False, None, None
        
        # Cập nhật thông tin giao dịch
        transaction.transaction_no = vnp_TransactionNo
        transaction.transaction_status = vnp_ResponseCode
        transaction.save()
        
        # Kiểm tra kết quả giao dịch
        if vnp_ResponseCode == '00':
            # Lấy user_id và package_id từ OrderInfo
            try:
                order_parts = vnp_OrderInfo.split('_')
                if len(order_parts) >= 2 and order_parts[0] == 'premium':
                    user_id = int(order_parts[1])
                    package_id = int(order_parts[2]) if len(order_parts) >= 3 else 1  # Mặc định gói 1 nếu không có
                    return True, user_id, package_id
            except (ValueError, IndexError):
                pass
        
        return False, None, None 
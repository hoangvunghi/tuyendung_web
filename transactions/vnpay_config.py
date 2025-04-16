import hashlib
import hmac
import urllib.parse
import random
import json
from datetime import datetime
from django.conf import settings
import socket
import struct

class VnPayConfig:
    # Cấu hình cho môi trường test của VNPay
    vnp_Version = "2.1.0"
    vnp_Command = "pay"
    vnp_TmnCode = "C98Y9W9D"  # Mã website tại VNPay
    vnp_HashSecret = "URKRP0T0KV3KP73EZLWERHJAEE6K2I82"  # Chuỗi bí mật
    vnp_Url = "https://sandbox.vnpayment.vn/paymentv2/vpcpay.html"
    vnp_ReturnUrl = "/api/vnpay/payment-return/"  # URL trả về sau khi thanh toán
    
    @staticmethod
    def hmacsha512(key, data):
        byteKey = key.encode('utf-8')
        byteData = data.encode('utf-8')
        return hmac.new(byteKey, byteData, hashlib.sha512).hexdigest()
    
    @staticmethod
    def get_client_ip(request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    @staticmethod
    def get_random_number(length):
        """Tạo chuỗi số ngẫu nhiên với độ dài xác định"""
        return ''.join(random.choice('0123456789') for _ in range(length)) 
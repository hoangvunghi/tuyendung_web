from django.shortcuts import render, redirect
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from .models import HistoryMoney, VnPayTransaction
from .serializers import HistoryMoneySerializer, VnPayTransactionSerializer
from base.permissions import IsTransactionOwner, IsAdminUser, AdminAccessPermission
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from base.pagination import CustomPagination
from base.utils import create_permission_class_with_admin_override
from .vnpay_service import VnPayService
from accounts.models import UserAccount
from django.http import HttpResponseRedirect
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
# Tạo các lớp quyền kết hợp với quyền admin
AdminOrTransactionOwner = create_permission_class_with_admin_override(IsTransactionOwner)

# Create your views here.

@swagger_auto_schema(
    method='get',
    operation_description="Lấy lịch sử giao dịch của người dùng hiện tại",
    manual_parameters=[
        openapi.Parameter(
            'page', openapi.IN_QUERY, 
            description="Số trang", 
            type=openapi.TYPE_INTEGER,
            required=False
        ),
        openapi.Parameter(
            'page_size', openapi.IN_QUERY, 
            description="Số lượng giao dịch mỗi trang", 
            type=openapi.TYPE_INTEGER,
            required=False
        ),
    ],
    responses={
        200: openapi.Response(
            description="Successful operation",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'data': openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'links': openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'next': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                                    'previous': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                                }
                            ),
                            'total': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'page': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'total_pages': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'page_size': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'results': openapi.Schema(
                                type=openapi.TYPE_ARRAY,
                                items=openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    properties={
                                        'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                        'user': openapi.Schema(type=openapi.TYPE_INTEGER),
                                        'amount': openapi.Schema(type=openapi.TYPE_NUMBER),
                                        'is_add_money': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                                        'description': openapi.Schema(type=openapi.TYPE_STRING),
                                        'balance_after': openapi.Schema(type=openapi.TYPE_NUMBER),
                                        'created_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                                    }
                                )
                            ),
                        }
                    )
                }
            )
        )
    },
    security=[{'Bearer': []}]
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, AdminOrTransactionOwner])
def get_history_money(request):
    history = HistoryMoney.objects.filter(user=request.user).order_by('-created_at')
    
    paginator = CustomPagination()
    paginated_history = paginator.paginate_queryset(history, request)
    
    serializer = HistoryMoneySerializer(paginated_history, many=True)
    return paginator.get_paginated_response(serializer.data)

@swagger_auto_schema(
    method='post',
    operation_description="Nạp tiền vào tài khoản",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['amount'],
        properties={
            'amount': openapi.Schema(type=openapi.TYPE_NUMBER, description="Số tiền nạp vào"),
            'description': openapi.Schema(type=openapi.TYPE_STRING, description="Mô tả giao dịch"),
        }
    ),
    responses={
        201: openapi.Response(
            description="Money added successfully",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'data': openapi.Schema(type=openapi.TYPE_OBJECT)
                }
            )
        ),
        400: openapi.Response(
            description="Bad request",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'errors': openapi.Schema(type=openapi.TYPE_OBJECT)
                }
            )
        )
    },
    security=[{'Bearer': []}]
)
@api_view(['POST'])
@permission_classes([IsAuthenticated, AdminAccessPermission])
def add_money(request):
    amount = request.data.get('amount')
    description = request.data.get('description', 'Nạp tiền')
    
    if not amount or float(amount) <= 0:
        return Response({
            'message': 'Invalid amount',
            'status': status.HTTP_400_BAD_REQUEST
        }, status=status.HTTP_400_BAD_REQUEST)
        
    try:
        # Tạo lịch sử giao dịch
        history = HistoryMoney.objects.create(
            user=request.user,
            amount=amount,
            is_add_money=True,
            description=description,
            balance_after=request.user.userinfo.balance + float(amount)
        )
        
        # Cập nhật số dư
        request.user.userinfo.balance += float(amount)
        request.user.userinfo.save()
        
        serializer = HistoryMoneySerializer(history)
        return Response({
            'message': 'Money added successfully',
            'status': status.HTTP_200_OK,
            'data': serializer.data
        })
    except Exception as e:
        return Response({
            'message': str(e),
            'status': status.HTTP_400_BAD_REQUEST
        }, status=status.HTTP_400_BAD_REQUEST)

@swagger_auto_schema(
    method='post',
    operation_description="Trừ tiền từ tài khoản",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['amount'],
        properties={
            'amount': openapi.Schema(type=openapi.TYPE_NUMBER, description="Số tiền trừ đi"),
            'description': openapi.Schema(type=openapi.TYPE_STRING, description="Mô tả giao dịch"),
        }
    ),
    responses={
        200: openapi.Response(
            description="Money subtracted successfully",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'data': openapi.Schema(type=openapi.TYPE_OBJECT)
                }
            )
        ),
        400: openapi.Response(
            description="Bad request",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'errors': openapi.Schema(type=openapi.TYPE_OBJECT)
                }
            )
        )
    },
    security=[{'Bearer': []}]
)
@api_view(['POST'])
@permission_classes([IsAuthenticated, AdminAccessPermission])
def subtract_money(request):
    amount = request.data.get('amount')
    description = request.data.get('description', 'Trừ tiền')
    
    if not amount or float(amount) <= 0:
        return Response({
            'message': 'Invalid amount',
            'status': status.HTTP_400_BAD_REQUEST
        }, status=status.HTTP_400_BAD_REQUEST)
        
    if request.user.userinfo.balance < float(amount):
        return Response({
            'message': 'Insufficient balance',
            'status': status.HTTP_400_BAD_REQUEST
        }, status=status.HTTP_400_BAD_REQUEST)
        
    try:
        # Tạo lịch sử giao dịch
        history = HistoryMoney.objects.create(
            user=request.user,
            amount=amount,
            is_add_money=False,
            description=description,
            balance_after=request.user.userinfo.balance - float(amount)
        )
        
        # Cập nhật số dư
        request.user.userinfo.balance -= float(amount)
        request.user.userinfo.save()
        
        serializer = HistoryMoneySerializer(history)
        return Response({
            'message': 'Money subtracted successfully',
            'status': status.HTTP_200_OK,
            'data': serializer.data
        })
    except Exception as e:
        return Response({
            'message': str(e),
            'status': status.HTTP_400_BAD_REQUEST
        }, status=status.HTTP_400_BAD_REQUEST)

@swagger_auto_schema(
    method='get',
    operation_description="Lấy tất cả giao dịch (chỉ dành cho admin)",
    manual_parameters=[
        openapi.Parameter(
            'page', openapi.IN_QUERY, 
            description="Số trang", 
            type=openapi.TYPE_INTEGER,
            required=False
        ),
        openapi.Parameter(
            'page_size', openapi.IN_QUERY, 
            description="Số lượng giao dịch mỗi trang", 
            type=openapi.TYPE_INTEGER,
            required=False
        ),
    ],
    responses={
        200: openapi.Response(
            description="Successful operation",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'data': openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'links': openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'next': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                                    'previous': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                                }
                            ),
                            'total': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'page': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'total_pages': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'page_size': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'results': openapi.Schema(
                                type=openapi.TYPE_ARRAY,
                                items=openapi.Schema(type=openapi.TYPE_OBJECT)
                            ),
                        }
                    )
                }
            )
        ),
        403: openapi.Response(
            description="Permission denied",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'detail': openapi.Schema(type=openapi.TYPE_STRING)
                }
            )
        )
    },
    security=[{'Bearer': []}]
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, AdminAccessPermission])
def get_all_transactions(request):
    transactions = HistoryMoney.objects.all().order_by('-created_at')
    
    paginator = CustomPagination()
    paginated_transactions = paginator.paginate_queryset(transactions, request)
    
    serializer = HistoryMoneySerializer(paginated_transactions, many=True)
    return paginator.get_paginated_response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated, AdminAccessPermission])
def get_all_history_money(request):
    history = HistoryMoney.objects.all().order_by('-created_at')
    paginator = CustomPagination()
    paginated_history = paginator.paginate_queryset(history, request)
    serializer = HistoryMoneySerializer(paginated_history, many=True)
    return paginator.get_paginated_response(serializer.data)

@swagger_auto_schema(
    method='post',
    operation_description="Tạo URL thanh toán VNPay",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['amount'],
        properties={
            'amount': openapi.Schema(type=openapi.TYPE_INTEGER, description="Số tiền thanh toán (VND)"),
        }
    ),
    responses={
        200: openapi.Response(
            description="Successful operation",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'data': openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'payment_url': openapi.Schema(type=openapi.TYPE_STRING),
                        }
                    )
                }
            )
        ),
        400: openapi.Response(
            description="Bad request",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                }
            )
        )
    },
    security=[{'Bearer': []}]
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_vnpay_payment(request):
    """
    Tạo URL thanh toán VNPay
    """
    amount = request.data.get('amount')
    
    if not amount or int(amount) <= 0:
        return Response({
            'message': 'Số tiền không hợp lệ',
            'status': status.HTTP_400_BAD_REQUEST
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Tạo URL thanh toán VNPay
        payment_url = VnPayService.create_payment_url(request, amount, request.user.id)
        
        return Response({
            'message': 'Tạo URL thanh toán thành công',
            'status': status.HTTP_200_OK,
            'data': {
                'payment_url': payment_url
            }
        })
    except Exception as e:
        return Response({
            'message': str(e),
            'status': status.HTTP_400_BAD_REQUEST
        }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def vnpay_payment_return(request):
    """
    Xử lý kết quả trả về từ VNPay
    """
    # Xử lý kết quả trả về từ VNPay
    is_success, user_id, package_id = VnPayService.process_return_url(request)
    
    if is_success:
        try:
            user = UserAccount.objects.get(id=user_id)
            user.is_premium = True
            
            # Xác định thời hạn premium dựa vào gói đã mua
            if package_id == 2:  # Gói năm
                user.premium_expiry = timezone.now() + timedelta(days=365)
            else:  # Gói tháng hoặc mặc định
                user.premium_expiry = timezone.now() + timedelta(days=30)
            
            user.save()
            
            # Lấy tên gói
            package_name = "Gói Premium Năm" if package_id == 2 else "Gói Premium Tháng"
            
            # Chuyển hướng đến URL thành công với thông tin gói
            return HttpResponseRedirect(
                redirect_to=f'http://localhost:5173/payment-success?package={package_id}&name={package_name}'
            )
        except UserAccount.DoesNotExist:
            pass
    
    # Nếu không thành công hoặc có lỗi
    return HttpResponseRedirect(redirect_to='http://localhost:5173/payment-failed')

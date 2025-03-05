from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from .models import HistoryMoney
from .serializers import HistoryMoneySerializer
from base.permissions import IsTransactionOwner, IsAdminUser

# Create your views here.

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsTransactionOwner])
def get_history_money(request):
    history = HistoryMoney.objects.filter(user=request.user).order_by('-created_at')
    serializer = HistoryMoneySerializer(history, many=True)
    return Response({
        'message': 'Transaction history retrieved successfully',
        'status': status.HTTP_200_OK,
        'data': serializer.data
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_money(request):
    serializer = HistoryMoneySerializer(data=request.data)
    if serializer.is_valid():
        # Tính toán balance_after
        last_transaction = HistoryMoney.objects.filter(user=request.user).order_by('-created_at').first()
        current_balance = last_transaction.balance_after if last_transaction else 0
        amount = serializer.validated_data['amount']
        
        serializer.save(
            user=request.user,
            is_add_money=True,
            balance_after=current_balance + amount
        )
        
        return Response({
            'message': 'Money added successfully',
            'status': status.HTTP_201_CREATED,
            'data': serializer.data
        }, status=status.HTTP_201_CREATED)
    return Response({
        'message': 'Adding money failed',
        'status': status.HTTP_400_BAD_REQUEST,
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def subtract_money(request):
    serializer = HistoryMoneySerializer(data=request.data)
    if serializer.is_valid():
        # Kiểm tra số dư
        last_transaction = HistoryMoney.objects.filter(user=request.user).order_by('-created_at').first()
        current_balance = last_transaction.balance_after if last_transaction else 0
        amount = serializer.validated_data['amount']
        
        if current_balance < amount:
            return Response({
                'message': 'Insufficient balance',
                'status': status.HTTP_400_BAD_REQUEST
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer.save(
            user=request.user,
            is_add_money=False,
            balance_after=current_balance - amount
        )
        
        return Response({
            'message': 'Money subtracted successfully',
            'status': status.HTTP_201_CREATED,
            'data': serializer.data
        }, status=status.HTTP_201_CREATED)
    return Response({
        'message': 'Subtracting money failed',
        'status': status.HTTP_400_BAD_REQUEST,
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def get_all_transactions(request):
    """Admin only: Xem tất cả giao dịch"""
    transactions = HistoryMoney.objects.all().order_by('-created_at')
    serializer = HistoryMoneySerializer(transactions, many=True)
    return Response({
        'message': 'All transactions retrieved successfully',
        'status': status.HTTP_200_OK,
        'data': serializer.data
    })

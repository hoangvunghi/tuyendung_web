from django.urls import path
from . import views

urlpatterns = [
    path('transactions/history/', views.get_history_money, name='get-history-money'),
    path('transactions/add-money/', views.add_money, name='add-money'),
    path('transactions/subtract-money/', views.subtract_money, name='subtract-money'),
    path('transactions/all/', views.get_all_transactions, name='get-all-transactions'),  # Admin only
    path('vnpay/create-payment/', views.create_vnpay_payment, name='create-vnpay-payment'),
    path('vnpay/payment-return/', views.vnpay_payment_return, name='vnpay-payment-return'),
] 
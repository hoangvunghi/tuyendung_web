from django.urls import path
from . import views

urlpatterns = [
    path('api/transactions/history/', views.get_history_money, name='get-history-money'),
    path('api/transactions/add-money/', views.add_money, name='add-money'),
    path('api/transactions/subtract-money/', views.subtract_money, name='subtract-money'),
    path('api/transactions/all/', views.get_all_transactions, name='get-all-transactions'),  # Admin only
] 
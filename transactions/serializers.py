from rest_framework import serializers
from .models import HistoryMoney, VnPayTransaction

class HistoryMoneySerializer(serializers.ModelSerializer):
    class Meta:
        model = HistoryMoney
        fields = '__all__'
        read_only_fields = ('user', 'created_at', 'modified_at') 

class VnPayTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = VnPayTransaction
        fields = '__all__'
        read_only_fields = ('user', 'created_at', 'modified_at', 'transaction_no', 'transaction_status') 
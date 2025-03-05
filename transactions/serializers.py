from rest_framework import serializers
from .models import HistoryMoney

class HistoryMoneySerializer(serializers.ModelSerializer):
    class Meta:
        model = HistoryMoney
        fields = '__all__'
        read_only_fields = ('user', 'created_at', 'modified_at') 
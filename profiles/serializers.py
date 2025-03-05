from rest_framework import serializers
from .models import UserInfo, Cv

class UserInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserInfo
        fields = '__all__'

class CvSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cv
        fields = '__all__'

class CvStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cv
        fields = ['status', 'note']
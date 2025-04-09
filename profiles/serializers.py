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
class CvPostSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cv
        fields = ['cv_file_url', 'status', 'name', 'email', 'phone_number', 'description']
class CvStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cv
        fields = ['status', 'note']
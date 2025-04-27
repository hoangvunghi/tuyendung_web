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
    
class CvUserSerializer(serializers.ModelSerializer):
    #Tôi muốn lấy thêm post title và post enterprise name và enterprise logo
    post_title = serializers.SerializerMethodField()
    enterprise_name = serializers.SerializerMethodField()
    enterprise_logo = serializers.SerializerMethodField()
    def get_post_title(self, obj):
        return obj.post.title
    def get_enterprise_name(self, obj):
        return obj.post.enterprise.company_name
    def get_enterprise_logo(self, obj):
        return obj.post.enterprise.logo_url
    
    class Meta:
        model = Cv
        fields = '__all__'

class CvPostSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cv
        fields = ['cv_file_url', 'status', 'name', 'email', 'phone_number', 'description', 'id']
class CvStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cv
        fields = ['status', 'note']
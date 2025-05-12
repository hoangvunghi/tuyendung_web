from rest_framework import serializers
from profiles.models import UserInfo
from .models import UserAccount

class UserSerializer(serializers.ModelSerializer):
    fullname = serializers.CharField(write_only=True)
    gender = serializers.ChoiceField(choices=UserInfo.GENDER_CHOICES, write_only=True)

    class Meta:
        model = UserAccount
        fields = ('email', 'username', 'password', 'fullname', 'gender')
        extra_kwargs = {'password': {'write_only': True}}

    def create_user(self, validated_data):
        user = UserAccount.objects.create_user(
            email=validated_data['email'],
            username=validated_data['username'],
            password=validated_data['password']
        )
        return user

    def create_user_info(self, user, fullname, gender):
        UserInfo.objects.create(user=user, fullname=fullname, gender=gender)

    def create(self, validated_data):
        fullname = validated_data.pop('fullname')
        gender = validated_data.pop('gender')
        user = self.create_user(validated_data)
        self.create_user_info(user, fullname, gender)
        return user
    
class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

class ResetPasswordSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True)

class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Mật khẩu mới và xác nhận mật khẩu không khớp nhau"})
        return data
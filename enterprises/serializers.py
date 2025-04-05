from rest_framework import serializers
from .models import EnterpriseEntity, PostEntity, FieldEntity, PositionEntity, CriteriaEntity
from base.cloudinary_utils import upload_image_to_cloudinary, delete_image_from_cloudinary

class EnterpriseSerializer(serializers.ModelSerializer):
    class Meta:
        model = EnterpriseEntity
        fields = '__all__'
        read_only_fields = ('user', 'created_at', 'modified_at')

class PostSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostEntity
        fields = '__all__'
        read_only_fields = ('created_at', 'modified_at')

class FieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = FieldEntity
        fields = '__all__'
        read_only_fields = ('created_at', 'modified_at')

class PositionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PositionEntity
        fields = '__all__'
        read_only_fields = ('created_at', 'modified_at')

class CriteriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = CriteriaEntity
        fields = '__all__'
        read_only_fields = ('user', 'created_at', 'modified_at')

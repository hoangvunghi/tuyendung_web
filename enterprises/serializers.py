from rest_framework import serializers
from .models import EnterpriseEntity, PostEntity, FieldEntity, PositionEntity, CriteriaEntity
from base.cloudinary_utils import upload_image_to_cloudinary, delete_image_from_cloudinary
import re

def strip_html_tags(text):
    if text:
        clean = re.compile('<.*?>')
        return re.sub(clean, '', text)
    return text

class EnterpriseSerializer(serializers.ModelSerializer):
    class Meta:
        model = EnterpriseEntity
        fields = '__all__'
        read_only_fields = ('user', 'created_at', 'modified_at')

class PostSerializer(serializers.ModelSerializer):
    position_name = serializers.CharField(source='position.name', read_only=True)
    enterprise_name = serializers.CharField(source='enterprise.company_name', read_only=True)
    field_name = serializers.CharField(source='field.name', read_only=True)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Strip HTML tags from text fields
        data['description'] = strip_html_tags(data.get('description'))
        data['required'] = strip_html_tags(data.get('required'))
        data['interest'] = strip_html_tags(data.get('interest'))
        return data

    class Meta:
        model = PostEntity
        fields = '__all__'
        read_only_fields = ('created_at', 'modified_at')

class PostUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostEntity
        fields = '__all__'
        read_only_fields = ('created_at', 'modified_at', 'is_active', 'enterprise', 'position', 'field')

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

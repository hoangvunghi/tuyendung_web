from rest_framework import serializers
from .models import EnterpriseEntity, CampaignEntity, PostEntity, FieldEntity, PositionEntity, CriteriaEntity

class EnterpriseSerializer(serializers.ModelSerializer):
    class Meta:
        model = EnterpriseEntity
        fields = '__all__'
        read_only_fields = ('user', 'created_at', 'modified_at')

class CampaignSerializer(serializers.ModelSerializer):
    class Meta:
        model = CampaignEntity
        fields = '__all__'
        read_only_fields = ('created_at', 'modified_at')

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

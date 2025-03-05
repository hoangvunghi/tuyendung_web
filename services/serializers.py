from rest_framework import serializers
from .models import TypeService, PackageEntity, PackageCampaign

class TypeServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = TypeService
        fields = '__all__'
        read_only_fields = ('created_at', 'modified_at')

class PackageSerializer(serializers.ModelSerializer):
    class Meta:
        model = PackageEntity
        fields = '__all__'
        read_only_fields = ('created_at', 'modified_at')

class PackageCampaignSerializer(serializers.ModelSerializer):
    class Meta:
        model = PackageCampaign
        fields = '__all__'
        read_only_fields = ('created_at',) 
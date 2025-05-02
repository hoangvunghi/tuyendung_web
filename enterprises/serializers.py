from rest_framework import serializers
from .models import EnterpriseEntity, PostEntity, FieldEntity, PositionEntity, CriteriaEntity, SavedPostEntity
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

class EnterpriseDetailSerializer(serializers.ModelSerializer):
    # def to_representation(self, instance):
    #     data = super().to_representation(instance)
    #     data['description'] = strip_html_tags(data.get('description'))
    #     data['field_of_activity'] = strip_html_tags(data.get('field_of_activity'))
    #     return data
    #Thêm một trường is_premium dựa vào doanh nghiệp đang được xem chứ không phải user đang login, trong model của doanh nghiệp có field user, trong user có is_premium
    is_premium = serializers.SerializerMethodField()
    def get_is_premium(self, obj):
        return obj.user.is_premium
    class Meta:
        model = EnterpriseEntity
        fields = 'company_name', 'address', 'description', 'email_company', 'field_of_activity', 'link_web_site', 'logo_url',  'background_image_url', 'phone_number', 'scale', 'tax', 'city', 'is_premium'
        read_only_fields = ('user', 'created_at', 'modified_at')

class PostSerializer(serializers.ModelSerializer):
    position_name = serializers.CharField(source='position.name', read_only=True)
    enterprise_name = serializers.CharField(source='enterprise.company_name', read_only=True)
    enterprise_logo = serializers.CharField(source='enterprise.logo_url', read_only=True)
    field_name = serializers.CharField(source='field.name', read_only=True)
    is_saved = serializers.SerializerMethodField()
    is_enterprise_premium = serializers.SerializerMethodField()

    def get_is_saved(self, obj):
        request = self.context.get('request', None)
        user = getattr(request, 'user', None)
        
        if user and user.is_authenticated:
            return SavedPostEntity.objects.filter(user=user, post=obj).exists()
        return False

    def get_is_enterprise_premium(self, obj):
        return obj.enterprise.user.is_premium

    # def to_representation(self, instance):
    #     data = super().to_representation(instance)
    #     # Strip HTML tags from text fields
    #     data['description'] = strip_html_tags(data.get('description'))
    #     data['required'] = strip_html_tags(data.get('required'))
    #     data['interest'] = strip_html_tags(data.get('interest'))
    #     return data
    class Meta:
        model = PostEntity
        fields = '__all__'
        read_only_fields = ('created_at', 'modified_at')

class PostEnterpriseSerializer(serializers.ModelSerializer):
    enterprise_name = serializers.CharField(source='enterprise.company_name', read_only=True)
    enterprise_logo = serializers.CharField(source='enterprise.logo_url', read_only=True)
    
    class Meta:
        model = PostEntity
        fields = ['title', 'enterprise_name', 'enterprise_logo', 'city', 'deadline', 'id', 'is_active']
        read_only_fields = ('created_at', 'modified_at')

class PostEnterpriseForEmployerSerializer(serializers.ModelSerializer):
    enterprise_name = serializers.CharField(source='enterprise.company_name', read_only=True)
    enterprise_logo = serializers.CharField(source='enterprise.logo_url', read_only=True)
    total_cvs = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = PostEntity
        fields = ['title', 'enterprise_name', 'enterprise_logo', 'city', 'deadline', 'id', 'is_active', 'total_cvs']
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

class SavedPostSerializer(serializers.ModelSerializer):
    post_detail = PostSerializer(source='post', read_only=True)
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Truyền context cho PostSerializer
        data['post_detail'] = PostSerializer(instance.post, context=self.context).data
        return data
    
    class Meta:
        model = SavedPostEntity
        fields = ['id', 'user', 'post', 'post_detail', 'created_at']
        read_only_fields = ('created_at',)
        extra_kwargs = {
            'user': {'write_only': True},
            'post': {'write_only': True}
        }

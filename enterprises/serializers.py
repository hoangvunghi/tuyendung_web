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

class PostSerializer(serializers.ModelSerializer):
    position = serializers.PrimaryKeyRelatedField(queryset=PositionEntity.objects.all())
    field = FieldSerializer(read_only=True)
    enterprise_name = serializers.CharField(source='enterprise.company_name', read_only=True)
    enterprise_logo = serializers.CharField(source='enterprise.logo_url', read_only=True)
    is_saved = serializers.SerializerMethodField()
    is_enterprise_premium = serializers.SerializerMethodField()
    matches_criteria = serializers.SerializerMethodField()

    class Meta:
        model = PostEntity
        fields = [
            'id', 'title', 'description', 'required', 'interest',
            'type_working', 'salary_min', 'salary_max', 'is_salary_negotiable',
            'quantity', 'city', 'district', 'position', 'field', 'created_at',
            'deadline', 'is_active', 'enterprise', 'enterprise_name', 'enterprise_logo',
            'is_saved', 'is_enterprise_premium', 'matches_criteria', 'experience', 'level', 'time_working'
        ]
        read_only_fields = ['created_at', 'is_active', 'is_saved', 'is_enterprise_premium', 'matches_criteria']

    def get_is_saved(self, obj):
        """Kiểm tra xem bài đăng có được lưu bởi người dùng hiện tại không"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return SavedPostEntity.objects.filter(user=request.user, post=obj).exists()
        return False

    def get_is_enterprise_premium(self, obj):
        """Kiểm tra xem doanh nghiệp có phải là premium không"""
        return obj.enterprise.user.is_premium
        
    def get_matches_criteria(self, obj):
        """Kiểm tra xem bài đăng có phù hợp với tiêu chí của người dùng không"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            try:
                criteria = CriteriaEntity.objects.get(user=request.user)
                score = 0
                
                # City (4 điểm)
                if criteria.city and obj.city and criteria.city.lower() == obj.city.lower():
                    score += 4
                    
                # Experience (3 điểm)
                if criteria.experience and obj.experience and criteria.experience.lower() == obj.experience.lower():
                    score += 3
                    
                # Type of working (3 điểm)
                if criteria.type_working and obj.type_working and criteria.type_working.lower() == obj.type_working.lower():
                    score += 3
                    
                # Scales (2 điểm)
                if criteria.scales and obj.enterprise and obj.enterprise.scale and criteria.scales.lower() == obj.enterprise.scale.lower():
                    score += 2
                    
                # Field (5 điểm)
                if criteria.field:
                    field_id = criteria.field.id if hasattr(criteria.field, 'id') else criteria.field
                    
                    # Kiểm tra field trực tiếp
                    if obj.field and ((hasattr(obj.field, 'id') and obj.field.id == field_id) or obj.field == field_id):
                        score += 5
                    # Kiểm tra field qua position
                    elif obj.position and obj.position.field and ((hasattr(obj.position.field, 'id') and obj.position.field.id == field_id) or obj.position.field == field_id):
                        score += 5
                
                # Position (5 điểm)
                if criteria.position:
                    position_id = criteria.position.id if hasattr(criteria.position, 'id') else criteria.position
                    
                    if obj.position and ((hasattr(obj.position, 'id') and obj.position.id == position_id) or obj.position == position_id):
                        score += 5
                
                # Salary (3 điểm)
                if criteria.salary_min and obj.salary_min and obj.salary_min >= criteria.salary_min:
                    score += 3
                
                # Công việc phù hợp khi điểm đạt tối thiểu 7 điểm
                return score >= 7
                
            except CriteriaEntity.DoesNotExist:
                pass
        
        return False

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

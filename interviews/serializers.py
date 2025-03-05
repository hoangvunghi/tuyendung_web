from rest_framework.serializers import ModelSerializer
from .models import Interview

class InterviewSerializer(ModelSerializer):
    class Meta:
        model = Interview
        fields = '__all__'

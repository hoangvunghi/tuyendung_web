from rest_framework.serializers import ModelSerializer, SerializerMethodField
from .models import Message

class MessageSerializer(ModelSerializer):
    recipient_fullname = SerializerMethodField()
    
    def get_recipient_fullname(self, obj):
        return obj.recipient.get_full_name() if obj.recipient else ''
    
    class Meta:
        model = Message
        fields = '__all__'
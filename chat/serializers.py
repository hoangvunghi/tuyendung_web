from rest_framework.serializers import ModelSerializer, SerializerMethodField
from .models import Message

class MessageSerializer(ModelSerializer):
    recipient_fullname = SerializerMethodField()
    sender_fullname = SerializerMethodField()
    conversation_partner_fullname = SerializerMethodField()
    conversation_partner_id = SerializerMethodField()
    
    def get_recipient_fullname(self, obj):
        return obj.recipient.get_full_name() if obj.recipient else ''
    
    def get_sender_fullname(self, obj):
        return obj.sender.get_full_name() if obj.sender else ''
    
    def get_conversation_partner_fullname(self, obj):
        # Lấy thông tin người dùng hiện tại từ context
        request = self.context.get('request', None)
        if not request or not request.user.is_authenticated:
            return ''
            
        # Xác định người đối thoại là sender hay recipient
        if obj.sender.id == request.user.id:
            return obj.recipient.get_full_name() if obj.recipient else ''
        else:
            return obj.sender.get_full_name() if obj.sender else ''
    
    def get_conversation_partner_id(self, obj):
        # Lấy thông tin người dùng hiện tại từ context
        request = self.context.get('request', None)
        if not request or not request.user.is_authenticated:
            return None
            
        # Xác định người đối thoại là sender hay recipient
        if obj.sender.id == request.user.id:
            return obj.recipient.id if obj.recipient else None
        else:
            return obj.sender.id if obj.sender else None
    
    class Meta:
        model = Message
        fields = '__all__'
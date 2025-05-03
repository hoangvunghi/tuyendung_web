from rest_framework import serializers
from .models import GeminiChatSession, GeminiChatMessage

class GeminiChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = GeminiChatMessage
        fields = ['id', 'role', 'content', 'created_at']
        read_only_fields = ['id', 'created_at']

class GeminiChatSessionSerializer(serializers.ModelSerializer):
    messages = GeminiChatMessageSerializer(many=True, read_only=True)
    
    class Meta:
        model = GeminiChatSession
        fields = ['id', 'session_id', 'title', 'is_active', 'created_at', 'updated_at', 'messages']
        read_only_fields = ['id', 'session_id', 'created_at', 'updated_at']

class ChatRequestSerializer(serializers.Serializer):
    message = serializers.CharField(required=True, allow_blank=False)
    session_id = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    
    def validate_message(self, value):
        if len(value.strip()) == 0:
            raise serializers.ValidationError("Tin nhắn không được để trống")
        return value 
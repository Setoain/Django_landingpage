from rest_framework import serializers
from .models import Email, ChatMessage

class EmailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Email
        fields = ['email']

    def validate_email(self, value):
        return value.lower().strip()


class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ['message', 'response', 'timestamp', 'session_id']
        read_only_fields = ['response', 'timestamp']

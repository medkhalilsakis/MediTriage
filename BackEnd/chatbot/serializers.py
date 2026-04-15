from rest_framework import serializers

from .models import ChatbotMessage, ChatbotSession


class ChatbotMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatbotMessage
        fields = ('id', 'session', 'sender', 'content', 'metadata', 'created_at')
        read_only_fields = ('created_at',)


class ChatbotSessionSerializer(serializers.ModelSerializer):
    messages = ChatbotMessageSerializer(many=True, read_only=True)

    class Meta:
        model = ChatbotSession
        fields = (
            'id',
            'patient',
            'title',
            'booked_appointment',
            'awaiting_appointment_confirmation',
            'latest_analysis',
            'is_closed',
            'messages',
            'created_at',
            'updated_at',
        )
        read_only_fields = (
            'created_at',
            'updated_at',
            'booked_appointment',
            'awaiting_appointment_confirmation',
            'latest_analysis',
        )
        extra_kwargs = {
            'patient': {'required': False},
        }


class ChatbotSendMessageSerializer(serializers.Serializer):
    content = serializers.CharField()
    wants_appointment = serializers.BooleanField(required=False, default=False)

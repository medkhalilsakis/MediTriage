from rest_framework import serializers

from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    recipient_email = serializers.EmailField(source='recipient.email', read_only=True)

    class Meta:
        model = Notification
        fields = ('id', 'recipient', 'recipient_email', 'notification_type', 'title', 'message', 'is_read', 'created_at')
        read_only_fields = ('created_at',)

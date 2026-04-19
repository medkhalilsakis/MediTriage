from rest_framework import serializers


class ConversationOpenSerializer(serializers.Serializer):
    recipient_id = serializers.IntegerField(min_value=1)


class DirectMessageCreateSerializer(serializers.Serializer):
    content = serializers.CharField(max_length=5000)

    def validate_content(self, value):
        normalized = str(value or '').strip()
        if not normalized:
            raise serializers.ValidationError('Message content cannot be empty.')
        return normalized


class PresenceHeartbeatSerializer(serializers.Serializer):
    is_online = serializers.BooleanField(required=False, default=True)

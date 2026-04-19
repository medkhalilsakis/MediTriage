from rest_framework import serializers

from .models import FollowUp, FollowUpAlert


class FollowUpAlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = FollowUpAlert
        fields = ('id', 'follow_up', 'alert_type', 'scheduled_at', 'status', 'message', 'created_at')
        read_only_fields = ('created_at',)


class FollowUpSerializer(serializers.ModelSerializer):
    patient_email = serializers.SerializerMethodField()
    doctor_email = serializers.EmailField(source='doctor.user.email', read_only=True)
    alerts = FollowUpAlertSerializer(many=True, read_only=True)

    class Meta:
        model = FollowUp
        fields = (
            'id',
            'patient',
            'patient_email',
            'doctor',
            'doctor_email',
            'consultation',
            'notes',
            'scheduled_at',
            'status',
            'alerts',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('created_at', 'updated_at')

    def get_patient_email(self, obj):
        patient = getattr(obj, 'patient', None)
        if not patient:
            return 'deleted user'
        return patient.get_public_identity_label()

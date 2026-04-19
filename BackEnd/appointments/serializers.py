from rest_framework import serializers
from django.utils import timezone

from .models import Appointment, AppointmentAdvanceOffer
from .scheduling import DEFAULT_END_TIME, DEFAULT_START_TIME


class AppointmentSerializer(serializers.ModelSerializer):
    patient_email = serializers.SerializerMethodField()
    doctor_email = serializers.EmailField(source='doctor.user.email', read_only=True)
    department_label = serializers.CharField(source='get_department_display', read_only=True)

    class Meta:
        model = Appointment
        fields = (
            'id',
            'patient',
            'patient_email',
            'doctor',
            'doctor_email',
            'scheduled_at',
            'status',
            'urgency_level',
            'department',
            'department_label',
            'reason',
            'notes',
            'last_staff_action_at',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('created_at', 'updated_at', 'last_staff_action_at')
        extra_kwargs = {
            'patient': {'required': False},
            'doctor': {'required': False},
            'scheduled_at': {'required': False},
            'department': {'required': False},
        }

    def validate(self, attrs):
        request = self.context.get('request')
        user = getattr(request, 'user', None)

        if user and user.is_authenticated and user.role == 'patient' and not self.partial:
            reason = (attrs.get('reason') or '').strip()
            if not reason:
                raise serializers.ValidationError({'reason': 'Please describe your illness.'})
            attrs['reason'] = reason

        scheduled_at = attrs.get('scheduled_at')
        if scheduled_at:
            local_slot = timezone.localtime(scheduled_at)
            if local_slot.weekday() == 6:
                raise serializers.ValidationError({'scheduled_at': 'Appointments cannot be scheduled on Sundays.'})

            if not (DEFAULT_START_TIME <= local_slot.time() < DEFAULT_END_TIME):
                raise serializers.ValidationError(
                    {
                        'scheduled_at': (
                            f"Appointments are allowed only between {DEFAULT_START_TIME.strftime('%H:%M')} "
                            f"and {DEFAULT_END_TIME.strftime('%H:%M')}."
                        )
                    }
                )

        return attrs

    def get_patient_email(self, obj):
        patient = getattr(obj, 'patient', None)
        if not patient:
            return 'deleted user'
        return patient.get_public_identity_label()


class AppointmentAdvanceOfferSerializer(serializers.ModelSerializer):
    patient_email = serializers.SerializerMethodField()
    doctor_email = serializers.EmailField(source='offered_doctor.user.email', read_only=True)
    current_scheduled_at = serializers.DateTimeField(source='appointment.scheduled_at', read_only=True)

    class Meta:
        model = AppointmentAdvanceOffer
        fields = (
            'id',
            'appointment',
            'patient_email',
            'doctor_email',
            'current_scheduled_at',
            'offered_slot',
            'status',
            'expires_at',
            'responded_at',
            'created_at',
        )
        read_only_fields = (
            'id',
            'appointment',
            'patient_email',
            'doctor_email',
            'current_scheduled_at',
            'offered_slot',
            'status',
            'expires_at',
            'responded_at',
            'created_at',
        )

    def get_patient_email(self, obj):
        patient = getattr(getattr(obj, 'appointment', None), 'patient', None)
        if not patient:
            return 'deleted user'
        return patient.get_public_identity_label()

from rest_framework import serializers

from .models import PatientProfile


class PatientProfileSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = PatientProfile
        fields = (
            'id',
            'user',
            'user_email',
            'dob',
            'gender',
            'blood_group',
            'allergies',
            'emergency_contact_name',
            'emergency_contact_phone',
            'address',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('created_at', 'updated_at')

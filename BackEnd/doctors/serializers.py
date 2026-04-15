from rest_framework import serializers

from .models import DoctorAvailabilitySlot, DoctorLeave, DoctorProfile


class DoctorAvailabilitySlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = DoctorAvailabilitySlot
        fields = ('id', 'doctor', 'weekday', 'start_time', 'end_time', 'is_active', 'created_at')
        read_only_fields = ('created_at',)


class DoctorProfileSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    department_label = serializers.CharField(source='get_department_display', read_only=True)
    availability_slots = DoctorAvailabilitySlotSerializer(many=True, read_only=True)

    class Meta:
        model = DoctorProfile
        fields = (
            'id',
            'user',
            'user_email',
            'specialization',
            'department',
            'department_label',
            'license_number',
            'years_of_experience',
            'consultation_fee',
            'bio',
            'availability_slots',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('created_at', 'updated_at')


class DoctorLeaveSerializer(serializers.ModelSerializer):
    doctor_email = serializers.EmailField(source='doctor.user.email', read_only=True)
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True)
    reviewed_by_email = serializers.EmailField(source='reviewed_by.email', read_only=True)
    status_label = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = DoctorLeave
        fields = (
            'id',
            'doctor',
            'doctor_email',
            'start_date',
            'end_date',
            'reason',
            'status',
            'status_label',
            'is_active',
            'created_by',
            'created_by_email',
            'reviewed_by',
            'reviewed_by_email',
            'reviewed_at',
            'review_note',
            'created_at',
            'updated_at',
        )
        read_only_fields = (
            'created_at',
            'updated_at',
            'created_by',
            'reviewed_by',
            'reviewed_at',
            'review_note',
            'status',
            'is_active',
        )
        extra_kwargs = {
            'doctor': {'required': False},
        }

    def validate(self, attrs):
        start_date = attrs.get('start_date', getattr(self.instance, 'start_date', None))
        end_date = attrs.get('end_date', getattr(self.instance, 'end_date', None))
        doctor = attrs.get('doctor', getattr(self.instance, 'doctor', None))
        status = attrs.get('status', getattr(self.instance, 'status', DoctorLeave.Status.PENDING))
        is_active = attrs.get('is_active', getattr(self.instance, 'is_active', False))
        should_validate_overlap = is_active or status == DoctorLeave.Status.APPROVED

        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError({'end_date': 'End date must be on or after start date.'})

        if doctor and start_date and end_date and should_validate_overlap:
            overlap = DoctorLeave.objects.filter(
                doctor=doctor,
                is_active=True,
                start_date__lte=end_date,
                end_date__gte=start_date,
            )
            if self.instance:
                overlap = overlap.exclude(pk=self.instance.pk)
            if overlap.exists():
                raise serializers.ValidationError(
                    {'detail': 'An active leave period already overlaps these dates for this doctor.'}
                )

        return attrs

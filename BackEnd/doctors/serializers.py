from rest_framework import serializers

from .models import DoctorAvailabilitySlot, DoctorLeave, DoctorProfile


class DoctorAvailabilitySlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = DoctorAvailabilitySlot
        fields = ('id', 'doctor', 'weekday', 'start_time', 'end_time', 'is_active', 'created_at')
        read_only_fields = ('created_at',)


class DoctorProfileSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_first_name = serializers.CharField(source='user.first_name', read_only=True)
    user_last_name = serializers.CharField(source='user.last_name', read_only=True)
    user_is_active = serializers.BooleanField(source='user.is_active', read_only=True)
    user_profile_image_url = serializers.SerializerMethodField()
    department_label = serializers.CharField(source='get_department_display', read_only=True)
    availability_slots = DoctorAvailabilitySlotSerializer(many=True, read_only=True)

    class Meta:
        model = DoctorProfile
        fields = (
            'id',
            'user',
            'user_email',
            'user_first_name',
            'user_last_name',
            'user_is_active',
            'user_profile_image_url',
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

    def get_user_profile_image_url(self, obj):
        if not obj.user.profile_image:
            return ''

        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(obj.user.profile_image.url)
        return obj.user.profile_image.url


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

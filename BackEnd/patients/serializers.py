from rest_framework import serializers

from .models import PatientProfile


class PatientProfileSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_first_name = serializers.CharField(source='user.first_name', read_only=True)
    user_last_name = serializers.CharField(source='user.last_name', read_only=True)
    user_is_active = serializers.BooleanField(source='user.is_active', read_only=True)
    user_profile_image_url = serializers.SerializerMethodField()

    class Meta:
        model = PatientProfile
        fields = (
            'id',
            'user',
            'user_email',
            'user_first_name',
            'user_last_name',
            'user_is_active',
            'user_profile_image_url',
            'dob',
            'gender',
            'blood_group',
            'allergies',
            'emergency_contact_name',
            'emergency_contact_phone',
            'address',
            'is_account_deleted',
            'account_deleted_at',
            'deleted_by',
            'created_at',
            'updated_at',
        )

    def get_user_profile_image_url(self, obj):
        if not obj.user.profile_image:
            return ''

        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(obj.user.profile_image.url)
        return obj.user.profile_image.url
        read_only_fields = (
            'user_email',
            'user_first_name',
            'user_last_name',
            'user_is_active',
            'is_account_deleted',
            'account_deleted_at',
            'deleted_by',
            'created_at',
            'updated_at',
        )

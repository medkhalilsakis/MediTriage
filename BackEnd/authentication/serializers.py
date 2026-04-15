from django.db import transaction
from django.contrib.auth import authenticate
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from patients.models import PatientProfile
from doctors.models import DoctorProfile

from .models import CustomUser


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ('id', 'email', 'username', 'first_name', 'last_name', 'role', 'phone_number', 'is_verified')


class AccountMeSerializer(serializers.ModelSerializer):
    dob = serializers.DateField(required=False, allow_null=True)
    gender = serializers.ChoiceField(
        required=False,
        allow_blank=True,
        choices=PatientProfile.Gender.choices,
    )
    blood_group = serializers.ChoiceField(
        required=False,
        allow_blank=True,
        choices=PatientProfile.BloodGroup.choices,
    )

    class Meta:
        model = CustomUser
        fields = (
            'id',
            'email',
            'username',
            'first_name',
            'last_name',
            'phone_number',
            'role',
            'dob',
            'gender',
            'blood_group',
        )
        read_only_fields = ('id', 'role')

    def to_representation(self, instance):
        data = super().to_representation(instance)
        profile = getattr(instance, 'patient_profile', None)
        data['dob'] = profile.dob.isoformat() if profile and profile.dob else None
        data['gender'] = profile.gender if profile else ''
        data['blood_group'] = profile.blood_group if profile else ''
        return data

    def update(self, instance, validated_data):
        dob = validated_data.pop('dob', serializers.empty)
        gender = validated_data.pop('gender', serializers.empty)
        blood_group = validated_data.pop('blood_group', serializers.empty)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if instance.role == CustomUser.Role.PATIENT:
            profile, _ = PatientProfile.objects.get_or_create(user=instance)
            profile_changed = False

            if dob is not serializers.empty:
                profile.dob = dob
                profile_changed = True
            if gender is not serializers.empty:
                profile.gender = gender
                profile_changed = True
            if blood_group is not serializers.empty:
                profile.blood_group = blood_group
                profile_changed = True

            if profile_changed:
                profile.save()

        return instance


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    specialization = serializers.CharField(required=False, allow_blank=True, write_only=True)
    department = serializers.ChoiceField(
        choices=DoctorProfile.Department.choices,
        required=False,
        write_only=True,
    )
    license_number = serializers.CharField(required=False, allow_blank=True, write_only=True)

    class Meta:
        model = CustomUser
        fields = (
            'id',
            'email',
            'username',
            'first_name',
            'last_name',
            'phone_number',
            'role',
            'password',
            'specialization',
            'department',
            'license_number',
        )

    def validate(self, attrs):
        role = attrs.get('role')

        if role == CustomUser.Role.DOCTOR:
            if not (attrs.get('specialization') or '').strip():
                raise serializers.ValidationError({'specialization': 'This field is required for doctors.'})
            if not attrs.get('department'):
                raise serializers.ValidationError({'department': 'This field is required for doctors.'})
            if not (attrs.get('license_number') or '').strip():
                raise serializers.ValidationError({'license_number': 'This field is required for doctors.'})

        return attrs

    def create(self, validated_data):
        password = validated_data.pop('password')

        specialization = validated_data.pop('specialization', '')
        department = validated_data.pop('department', '')
        license_number = validated_data.pop('license_number', '')

        with transaction.atomic():
            user = CustomUser.objects.create_user(password=password, **validated_data)

            if user.role == CustomUser.Role.PATIENT:
                PatientProfile.objects.get_or_create(user=user)

            if user.role == CustomUser.Role.DOCTOR:
                DoctorProfile.objects.create(
                    user=user,
                    specialization=specialization.strip(),
                    department=department,
                    license_number=license_number.strip(),
                )

        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        user = authenticate(request=self.context.get('request'), username=email, password=password)
        if not user:
            raise serializers.ValidationError('Invalid credentials.')
        if not user.is_active:
            raise serializers.ValidationError('User account is inactive.')
        attrs['user'] = user
        return attrs


class AuthResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()
    user = UserSerializer()

    @staticmethod
    def build(user):
        token = RefreshToken.for_user(user)
        return {
            'access': str(token.access_token),
            'refresh': str(token),
            'user': UserSerializer(user).data,
        }

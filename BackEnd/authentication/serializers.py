from django.contrib.auth import authenticate
from django.db import IntegrityError, transaction
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from doctors.models import DoctorProfile
from patients.models import PatientProfile

from .models import CustomUser


class UserSerializer(serializers.ModelSerializer):
    profile_image_url = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = (
            'id',
            'email',
            'username',
            'first_name',
            'last_name',
            'role',
            'phone_number',
            'profile_image_url',
            'is_verified',
        )

    def get_profile_image_url(self, obj):
        if not obj.profile_image:
            return ''

        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(obj.profile_image.url)
        return obj.profile_image.url


class AccountMeSerializer(serializers.ModelSerializer):
    profile_image = serializers.FileField(required=False, allow_null=True)
    profile_image_url = serializers.SerializerMethodField(read_only=True)

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
    allergies = serializers.CharField(required=False, allow_blank=True)
    emergency_contact_name = serializers.CharField(required=False, allow_blank=True)
    emergency_contact_phone = serializers.CharField(required=False, allow_blank=True)
    address = serializers.CharField(required=False, allow_blank=True)

    specialization = serializers.CharField(required=False, allow_blank=True)
    department = serializers.ChoiceField(required=False, choices=DoctorProfile.Department.choices)
    license_number = serializers.CharField(required=False, allow_blank=True)
    years_of_experience = serializers.IntegerField(required=False, min_value=0)
    consultation_fee = serializers.DecimalField(required=False, max_digits=10, decimal_places=2, min_value=0)
    bio = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = CustomUser
        fields = (
            'id',
            'email',
            'username',
            'first_name',
            'last_name',
            'phone_number',
            'profile_image',
            'profile_image_url',
            'role',
            'dob',
            'gender',
            'blood_group',
            'allergies',
            'emergency_contact_name',
            'emergency_contact_phone',
            'address',
            'specialization',
            'department',
            'license_number',
            'years_of_experience',
            'consultation_fee',
            'bio',
        )
        read_only_fields = ('id', 'role')

    def get_profile_image_url(self, obj):
        if not obj.profile_image:
            return ''

        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(obj.profile_image.url)
        return obj.profile_image.url

    def to_representation(self, instance):
        data = super().to_representation(instance)
        patient_profile = PatientProfile.objects.filter(user=instance).first()
        doctor_profile = DoctorProfile.objects.filter(user=instance).first()

        data['dob'] = patient_profile.dob.isoformat() if patient_profile and patient_profile.dob else None
        data['gender'] = patient_profile.gender if patient_profile else ''
        data['blood_group'] = patient_profile.blood_group if patient_profile else ''
        data['allergies'] = patient_profile.allergies if patient_profile else ''
        data['emergency_contact_name'] = patient_profile.emergency_contact_name if patient_profile else ''
        data['emergency_contact_phone'] = patient_profile.emergency_contact_phone if patient_profile else ''
        data['address'] = patient_profile.address if patient_profile else ''

        data['specialization'] = doctor_profile.specialization if doctor_profile else ''
        data['department'] = doctor_profile.department if doctor_profile else ''
        data['license_number'] = doctor_profile.license_number if doctor_profile else ''
        data['years_of_experience'] = doctor_profile.years_of_experience if doctor_profile else 0
        data['consultation_fee'] = str(doctor_profile.consultation_fee) if doctor_profile else '0.00'
        data['bio'] = doctor_profile.bio if doctor_profile else ''
        return data

    def validate_profile_image(self, value):
        if value in [None, '']:
            return value

        allowed_types = {'image/jpeg', 'image/png', 'image/webp'}
        content_type = getattr(value, 'content_type', '')
        if content_type and content_type not in allowed_types:
            raise serializers.ValidationError('Profile image must be JPG, PNG, or WEBP.')
        return value

    def validate(self, attrs):
        if self.instance and self.instance.role == CustomUser.Role.DOCTOR:
            candidate_license = attrs.get('license_number', serializers.empty)
            if candidate_license is not serializers.empty:
                normalized = str(candidate_license or '').strip()
                if not normalized:
                    raise serializers.ValidationError({'license_number': 'This field cannot be empty for doctors.'})

                conflict = DoctorProfile.objects.filter(license_number__iexact=normalized).exclude(user=self.instance)
                if conflict.exists():
                    raise serializers.ValidationError({'license_number': 'This license number is already registered.'})

                attrs['license_number'] = normalized

        return attrs

    def update(self, instance, validated_data):
        dob = validated_data.pop('dob', serializers.empty)
        gender = validated_data.pop('gender', serializers.empty)
        blood_group = validated_data.pop('blood_group', serializers.empty)
        allergies = validated_data.pop('allergies', serializers.empty)
        emergency_contact_name = validated_data.pop('emergency_contact_name', serializers.empty)
        emergency_contact_phone = validated_data.pop('emergency_contact_phone', serializers.empty)
        address = validated_data.pop('address', serializers.empty)

        specialization = validated_data.pop('specialization', serializers.empty)
        department = validated_data.pop('department', serializers.empty)
        license_number = validated_data.pop('license_number', serializers.empty)
        years_of_experience = validated_data.pop('years_of_experience', serializers.empty)
        consultation_fee = validated_data.pop('consultation_fee', serializers.empty)
        bio = validated_data.pop('bio', serializers.empty)

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
            if allergies is not serializers.empty:
                profile.allergies = allergies
                profile_changed = True
            if emergency_contact_name is not serializers.empty:
                profile.emergency_contact_name = emergency_contact_name
                profile_changed = True
            if emergency_contact_phone is not serializers.empty:
                profile.emergency_contact_phone = emergency_contact_phone
                profile_changed = True
            if address is not serializers.empty:
                profile.address = address
                profile_changed = True

            if profile_changed:
                profile.save()

        if instance.role == CustomUser.Role.DOCTOR:
            profile, _ = DoctorProfile.objects.get_or_create(
                user=instance,
                defaults={
                    'specialization': 'General specialist',
                    'department': DoctorProfile.Department.GENERAL_MEDICINE,
                    'license_number': f'DOC-{instance.id:06d}',
                },
            )

            doctor_changed = False
            if specialization is not serializers.empty:
                profile.specialization = str(specialization).strip() or profile.specialization
                doctor_changed = True
            if department is not serializers.empty:
                profile.department = department
                doctor_changed = True
            if license_number is not serializers.empty:
                profile.license_number = str(license_number).strip()
                doctor_changed = True
            if years_of_experience is not serializers.empty:
                profile.years_of_experience = years_of_experience
                doctor_changed = True
            if consultation_fee is not serializers.empty:
                profile.consultation_fee = consultation_fee
                doctor_changed = True
            if bio is not serializers.empty:
                profile.bio = bio
                doctor_changed = True

            if doctor_changed:
                profile.save()

        return instance


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    specialization = serializers.CharField(required=False, allow_blank=True, write_only=True)
    department = serializers.ChoiceField(
        choices=DoctorProfile.Department.choices,
        required=False,
        allow_blank=True,
        allow_null=True,
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
            specialization = (attrs.get('specialization') or '').strip()
            license_number = (attrs.get('license_number') or '').strip()

            if not specialization:
                raise serializers.ValidationError({'specialization': 'This field is required for doctors.'})
            if not attrs.get('department'):
                raise serializers.ValidationError({'department': 'This field is required for doctors.'})
            if not license_number:
                raise serializers.ValidationError({'license_number': 'This field is required for doctors.'})

            if DoctorProfile.objects.filter(license_number__iexact=license_number).exists():
                raise serializers.ValidationError({'license_number': 'This license number is already registered.'})

            attrs['specialization'] = specialization
            attrs['license_number'] = license_number

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
                try:
                    DoctorProfile.objects.create(
                        user=user,
                        specialization=specialization.strip(),
                        department=department,
                        license_number=license_number.strip(),
                    )
                except IntegrityError as exc:
                    if 'license_number' in str(exc).lower():
                        raise serializers.ValidationError({'license_number': 'This license number is already registered.'}) from exc
                    raise

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
    def build(user, request=None):
        token = RefreshToken.for_user(user)
        context = {'request': request} if request else {}
        return {
            'access': str(token.access_token),
            'refresh': str(token),
            'user': UserSerializer(user, context=context).data,
        }

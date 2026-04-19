from django.utils import timezone
from rest_framework import serializers

from .models import Consultation, DoctorOperation, MedicalDocument, MedicalDocumentRequest, MedicalRecord
from .operations import validate_operation_schedule_conflicts

SLOT_DURATION_MINUTES = 30


class ConsultationSerializer(serializers.ModelSerializer):
    doctor_email = serializers.EmailField(source='doctor.user.email', read_only=True)
    patient_email = serializers.SerializerMethodField()
    out_of_specialty_validated_by_email = serializers.EmailField(source='out_of_specialty_validated_by.email', read_only=True)
    redirected_to_doctor_email = serializers.EmailField(source='redirected_to_doctor.user.email', read_only=True)

    class Meta:
        model = Consultation
        fields = (
            'id',
            'medical_record',
            'appointment',
            'doctor',
            'doctor_email',
            'patient_email',
            'chatbot_diagnosis',
            'diagnosis',
            'vitals',
            'anamnesis',
            'icd10_code',
            'treatment_plan',
            'out_of_specialty_confirmed',
            'out_of_specialty_opinion',
            'out_of_specialty_validated_at',
            'out_of_specialty_validated_by',
            'out_of_specialty_validated_by_email',
            'redirect_to_colleague',
            'redirect_note',
            'redirected_to_doctor',
            'redirected_to_doctor_email',
            'redirected_appointment',
            'created_at',
            'updated_at',
        )
        read_only_fields = (
            'out_of_specialty_confirmed',
            'out_of_specialty_opinion',
            'out_of_specialty_validated_at',
            'out_of_specialty_validated_by',
            'out_of_specialty_validated_by_email',
            'redirect_to_colleague',
            'redirect_note',
            'redirected_to_doctor',
            'redirected_to_doctor_email',
            'redirected_appointment',
            'created_at',
            'updated_at',
        )

    def get_patient_email(self, obj):
        patient = getattr(getattr(obj, 'medical_record', None), 'patient', None)
        if not patient:
            return 'deleted user'
        return patient.get_public_identity_label()


class MedicalDocumentSerializer(serializers.ModelSerializer):
    patient_email = serializers.SerializerMethodField()
    doctor_email = serializers.EmailField(source='uploaded_by_doctor.user.email', read_only=True)
    reviewed_by_email = serializers.EmailField(source='reviewed_by.user.email', read_only=True)
    medical_record_patient_email = serializers.SerializerMethodField()
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = MedicalDocument
        fields = (
            'id',
            'medical_record',
            'medical_record_patient_email',
            'request',
            'document_type',
            'title',
            'notes',
            'file',
            'file_url',
            'review_status',
            'review_note',
            'uploaded_by_patient',
            'patient_email',
            'uploaded_by_doctor',
            'doctor_email',
            'reviewed_by',
            'reviewed_by_email',
            'uploaded_at',
            'reviewed_at',
        )
        read_only_fields = (
            'uploaded_by_patient',
            'uploaded_by_doctor',
            'reviewed_by',
            'uploaded_at',
            'reviewed_at',
        )

    def get_file_url(self, obj):
        if not obj.file:
            return ''

        request = self.context.get('request')
        url = obj.file.url
        if request:
            return request.build_absolute_uri(url)
        return url

    def get_patient_email(self, obj):
        patient = getattr(obj, 'uploaded_by_patient', None)
        if not patient:
            return 'deleted user'
        return patient.get_public_identity_label()

    def get_medical_record_patient_email(self, obj):
        patient = getattr(getattr(obj, 'medical_record', None), 'patient', None)
        if not patient:
            return 'deleted user'
        return patient.get_public_identity_label()


class MedicalDocumentRequestSerializer(serializers.ModelSerializer):
    patient_email = serializers.SerializerMethodField()
    doctor_email = serializers.EmailField(source='doctor.user.email', read_only=True)
    documents = MedicalDocumentSerializer(many=True, read_only=True)

    class Meta:
        model = MedicalDocumentRequest
        fields = (
            'id',
            'medical_record',
            'patient_email',
            'doctor',
            'doctor_email',
            'request_type',
            'title',
            'description',
            'requested_items',
            'due_date',
            'status',
            'review_note',
            'closed_at',
            'documents',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('closed_at', 'created_at', 'updated_at')
        extra_kwargs = {
            'doctor': {'required': False},
        }

    def validate_requested_items(self, value):
        if value in [None, '']:
            return []
        if not isinstance(value, list):
            raise serializers.ValidationError('requested_items must be an array of text items.')

        normalized = []
        for item in value:
            text = str(item).strip()
            if not text:
                continue
            normalized.append(text)
        return normalized

    def get_patient_email(self, obj):
        patient = getattr(getattr(obj, 'medical_record', None), 'patient', None)
        if not patient:
            return 'deleted user'
        return patient.get_public_identity_label()


class MedicalRecordSerializer(serializers.ModelSerializer):
    patient_email = serializers.SerializerMethodField()
    consultations = ConsultationSerializer(many=True, read_only=True)
    operations = serializers.SerializerMethodField()
    document_requests = MedicalDocumentRequestSerializer(many=True, read_only=True)
    documents = MedicalDocumentSerializer(many=True, read_only=True)

    class Meta:
        model = MedicalRecord
        fields = (
            'id',
            'patient',
            'patient_email',
            'patient_full_name',
            'patient_date_of_birth',
            'patient_gender',
            'patient_phone',
            'patient_address',
            'emergency_contact_name',
            'emergency_contact_phone',
            'social_security_number',
            'administrative_notes',
            'consultation_motive',
            'medical_background',
            'current_illness_history',
            'clinical_examination',
            'complementary_exams',
            'diagnostic_summary',
            'treatment_management',
            'follow_up_plan',
            'annex_notes',
            'specialty_assessments',
            'longitudinal_metrics',
            'chronic_conditions',
            'surgeries_history',
            'family_history',
            'immunizations',
            'status',
            'closed_at',
            'archived_at',
            'archived_by',
            'consultations',
            'operations',
            'document_requests',
            'documents',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('closed_at', 'archived_at', 'archived_by', 'created_at', 'updated_at')

    def get_operations(self, obj):
        operations = obj.operations.select_related('doctor__user', 'finished_by').all()
        return DoctorOperationSerializer(operations, many=True, context=self.context).data

    def get_patient_email(self, obj):
        patient = getattr(obj, 'patient', None)
        if not patient:
            return 'deleted user'
        return patient.get_public_identity_label()


class DoctorOperationSerializer(serializers.ModelSerializer):
    doctor_email = serializers.EmailField(source='doctor.user.email', read_only=True)
    patient_email = serializers.SerializerMethodField()
    finished_by_email = serializers.EmailField(source='finished_by.email', read_only=True)
    is_blocking_now = serializers.SerializerMethodField()

    class Meta:
        model = DoctorOperation
        fields = (
            'id',
            'medical_record',
            'consultation',
            'doctor',
            'doctor_email',
            'patient_email',
            'operation_name',
            'details',
            'scheduled_start',
            'expected_duration_minutes',
            'expected_end_at',
            'release_at',
            'finished_at',
            'finished_by',
            'finished_by_email',
            'is_blocking_now',
            'created_at',
            'updated_at',
        )
        read_only_fields = (
            'expected_end_at',
            'release_at',
            'finished_at',
            'finished_by',
            'created_at',
            'updated_at',
        )
        extra_kwargs = {
            'consultation': {'required': False, 'allow_null': True},
        }

    def validate_expected_duration_minutes(self, value):
        if value < SLOT_DURATION_MINUTES:
            raise serializers.ValidationError(f'Operation duration must be at least {SLOT_DURATION_MINUTES} minutes.')
        return value

    def validate(self, attrs):
        doctor = attrs.get('doctor') or getattr(self.instance, 'doctor', None)
        medical_record = attrs.get('medical_record') or getattr(self.instance, 'medical_record', None)
        consultation = attrs.get('consultation') or getattr(self.instance, 'consultation', None)
        scheduled_start = attrs.get('scheduled_start') or getattr(self.instance, 'scheduled_start', None)
        expected_duration_minutes = attrs.get('expected_duration_minutes')
        if expected_duration_minutes is None:
            expected_duration_minutes = getattr(self.instance, 'expected_duration_minutes', None)

        if consultation and medical_record and consultation.medical_record_id != medical_record.id:
            raise serializers.ValidationError({'consultation': 'Consultation must belong to the selected medical record.'})

        if doctor and consultation and consultation.doctor_id != doctor.id:
            raise serializers.ValidationError({'consultation': 'Consultation doctor must match operation doctor.'})

        if scheduled_start:
            local_slot = timezone.localtime(scheduled_start).replace(second=0, microsecond=0)
            if local_slot.minute % SLOT_DURATION_MINUTES != 0:
                raise serializers.ValidationError(
                    {'scheduled_start': f'Operation start must align with {SLOT_DURATION_MINUTES}-minute slots.'}
                )
            attrs['scheduled_start'] = local_slot

        if doctor and scheduled_start and expected_duration_minutes:
            validate_operation_schedule_conflicts(
                doctor=doctor,
                scheduled_start=attrs.get('scheduled_start', scheduled_start),
                expected_duration_minutes=expected_duration_minutes,
                exclude_operation_id=getattr(self.instance, 'id', None),
            )

        return attrs

    def get_is_blocking_now(self, obj):
        now = timezone.now()
        return obj.scheduled_start <= now < obj.release_at

    def get_patient_email(self, obj):
        patient = getattr(getattr(obj, 'medical_record', None), 'patient', None)
        if not patient:
            return 'deleted user'
        return patient.get_public_identity_label()

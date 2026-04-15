from rest_framework import serializers

from .models import Consultation, MedicalDocument, MedicalDocumentRequest, MedicalRecord


class ConsultationSerializer(serializers.ModelSerializer):
    doctor_email = serializers.EmailField(source='doctor.user.email', read_only=True)
    patient_email = serializers.EmailField(source='medical_record.patient.user.email', read_only=True)

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
            'created_at',
            'updated_at',
        )
        read_only_fields = ('created_at', 'updated_at')


class MedicalDocumentSerializer(serializers.ModelSerializer):
    patient_email = serializers.EmailField(source='uploaded_by_patient.user.email', read_only=True)
    doctor_email = serializers.EmailField(source='uploaded_by_doctor.user.email', read_only=True)
    reviewed_by_email = serializers.EmailField(source='reviewed_by.user.email', read_only=True)
    medical_record_patient_email = serializers.EmailField(source='medical_record.patient.user.email', read_only=True)
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


class MedicalDocumentRequestSerializer(serializers.ModelSerializer):
    patient_email = serializers.EmailField(source='medical_record.patient.user.email', read_only=True)
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


class MedicalRecordSerializer(serializers.ModelSerializer):
    patient_email = serializers.EmailField(source='patient.user.email', read_only=True)
    consultations = ConsultationSerializer(many=True, read_only=True)
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
            'document_requests',
            'documents',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('closed_at', 'archived_at', 'archived_by', 'created_at', 'updated_at')

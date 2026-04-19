from rest_framework import serializers

from .models import Prescription, PrescriptionItem


class PrescriptionItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrescriptionItem
        fields = ('id', 'medication', 'dosage', 'frequency', 'duration', 'instructions')


class PrescriptionSerializer(serializers.ModelSerializer):
    items = PrescriptionItemSerializer(many=True)
    doctor_email = serializers.EmailField(source='doctor.user.email', read_only=True)
    patient_email = serializers.SerializerMethodField()

    class Meta:
        model = Prescription
        fields = (
            'id',
            'consultation',
            'doctor',
            'doctor_email',
            'patient',
            'patient_email',
            'notes',
            'items',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('created_at', 'updated_at')

    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        prescription = Prescription.objects.create(**validated_data)
        for item_data in items_data:
            PrescriptionItem.objects.create(prescription=prescription, **item_data)
        return prescription

    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if items_data is not None:
            instance.items.all().delete()
            for item_data in items_data:
                PrescriptionItem.objects.create(prescription=instance, **item_data)
        return instance

    def get_patient_email(self, obj):
        patient = getattr(obj, 'patient', None)
        if not patient:
            return 'deleted user'
        return patient.get_public_identity_label()

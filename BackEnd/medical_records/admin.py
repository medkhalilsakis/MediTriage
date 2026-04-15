from django.contrib import admin

from .models import Consultation, MedicalDocument, MedicalDocumentRequest, MedicalRecord


@admin.register(MedicalRecord)
class MedicalRecordAdmin(admin.ModelAdmin):
	list_display = ('id', 'patient', 'status', 'created_at')
	search_fields = ('patient__user__email',)
	list_filter = ('status',)


@admin.register(Consultation)
class ConsultationAdmin(admin.ModelAdmin):
	list_display = ('id', 'medical_record', 'doctor', 'icd10_code', 'created_at')
	search_fields = ('diagnosis', 'icd10_code', 'doctor__user__email')


@admin.register(MedicalDocumentRequest)
class MedicalDocumentRequestAdmin(admin.ModelAdmin):
	list_display = ('id', 'medical_record', 'doctor', 'request_type', 'status', 'due_date', 'created_at')
	search_fields = ('title', 'description', 'medical_record__patient__user__email', 'doctor__user__email')
	list_filter = ('request_type', 'status')


@admin.register(MedicalDocument)
class MedicalDocumentAdmin(admin.ModelAdmin):
	list_display = ('id', 'medical_record', 'title', 'document_type', 'review_status', 'uploaded_at')
	search_fields = ('title', 'medical_record__patient__user__email')
	list_filter = ('document_type', 'review_status')

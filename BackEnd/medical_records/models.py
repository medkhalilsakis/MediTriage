from datetime import timedelta

from django.db import models
from django.db.models import F, Q
from django.utils import timezone


class MedicalRecord(models.Model):
	class Status(models.TextChoices):
		ACTIVE = "active", "Active"
		CLOSED = "closed", "Closed"
		ARCHIVED = "archived", "Archived"

	patient = models.OneToOneField(
		"patients.PatientProfile",
		on_delete=models.CASCADE,
		related_name="medical_record",
	)
	patient_full_name = models.CharField(max_length=160, blank=True)
	patient_date_of_birth = models.DateField(null=True, blank=True)
	patient_gender = models.CharField(max_length=20, blank=True)
	patient_phone = models.CharField(max_length=20, blank=True)
	patient_address = models.TextField(blank=True)
	emergency_contact_name = models.CharField(max_length=120, blank=True)
	emergency_contact_phone = models.CharField(max_length=20, blank=True)
	social_security_number = models.CharField(max_length=60, blank=True)

	administrative_notes = models.TextField(blank=True)
	consultation_motive = models.TextField(blank=True)
	medical_background = models.TextField(blank=True)
	current_illness_history = models.TextField(blank=True)
	clinical_examination = models.TextField(blank=True)
	complementary_exams = models.TextField(blank=True)
	diagnostic_summary = models.TextField(blank=True)
	treatment_management = models.TextField(blank=True)
	follow_up_plan = models.TextField(blank=True)
	annex_notes = models.TextField(blank=True)
	specialty_assessments = models.JSONField(default=list, blank=True)
	longitudinal_metrics = models.JSONField(default=list, blank=True)

	chronic_conditions = models.TextField(blank=True)
	surgeries_history = models.TextField(blank=True)
	family_history = models.TextField(blank=True)
	immunizations = models.TextField(blank=True)
	status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
	closed_at = models.DateTimeField(null=True, blank=True)
	archived_at = models.DateTimeField(null=True, blank=True)
	archived_by = models.ForeignKey(
		"authentication.CustomUser",
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name="archived_medical_records",
	)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	def __str__(self):
		return f"MedicalRecord<{self.patient.user.email}>"


class Consultation(models.Model):
	medical_record = models.ForeignKey(
		MedicalRecord,
		on_delete=models.CASCADE,
		related_name="consultations",
	)
	appointment = models.OneToOneField(
		"appointments.Appointment",
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name="consultation",
	)
	doctor = models.ForeignKey(
		"doctors.DoctorProfile",
		on_delete=models.CASCADE,
		related_name="consultations",
	)
	chatbot_diagnosis = models.TextField(blank=True)
	diagnosis = models.TextField()
	vitals = models.JSONField(default=dict, blank=True)
	anamnesis = models.TextField(blank=True)
	icd10_code = models.CharField(max_length=20, blank=True)
	treatment_plan = models.TextField(blank=True)
	out_of_specialty_confirmed = models.BooleanField(default=False)
	out_of_specialty_opinion = models.TextField(blank=True)
	out_of_specialty_validated_at = models.DateTimeField(null=True, blank=True)
	out_of_specialty_validated_by = models.ForeignKey(
		"authentication.CustomUser",
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name="validated_out_of_specialty_consultations",
	)
	redirect_to_colleague = models.BooleanField(default=False)
	redirect_note = models.TextField(blank=True)
	redirected_to_doctor = models.ForeignKey(
		"doctors.DoctorProfile",
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name="received_out_of_specialty_referrals",
	)
	redirected_appointment = models.ForeignKey(
		"appointments.Appointment",
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name="out_of_specialty_origin_consultations",
	)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ["-created_at"]

	def __str__(self):
		return f"Consultation #{self.id} - {self.doctor.user.email}"


class DoctorOperation(models.Model):
	medical_record = models.ForeignKey(
		MedicalRecord,
		on_delete=models.CASCADE,
		related_name="operations",
	)
	consultation = models.ForeignKey(
		Consultation,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name="operations",
	)
	doctor = models.ForeignKey(
		"doctors.DoctorProfile",
		on_delete=models.CASCADE,
		related_name="operations",
	)
	operation_name = models.CharField(max_length=180)
	details = models.TextField(blank=True)
	scheduled_start = models.DateTimeField()
	expected_duration_minutes = models.PositiveIntegerField(default=120)
	expected_end_at = models.DateTimeField()
	release_at = models.DateTimeField()
	finished_at = models.DateTimeField(null=True, blank=True)
	finished_by = models.ForeignKey(
		"authentication.CustomUser",
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name="finished_operations",
	)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ["-scheduled_start", "-created_at"]
		constraints = [
			models.CheckConstraint(
				condition=Q(expected_duration_minutes__gt=0),
				name="doctor_operation_duration_positive",
			),
			models.CheckConstraint(
				condition=Q(release_at__gte=F("scheduled_start")),
				name="doctor_operation_release_after_start",
			),
		]
		indexes = [
			models.Index(fields=["doctor", "scheduled_start"]),
			models.Index(fields=["doctor", "release_at"]),
		]

	def save(self, *args, **kwargs):
		expected_end = self.scheduled_start + timedelta(minutes=int(self.expected_duration_minutes or 0))
		self.expected_end_at = expected_end
		if self.finished_at:
			self.release_at = self.finished_at
		else:
			self.release_at = expected_end + timedelta(hours=1)
		super().save(*args, **kwargs)

	def mark_finished(self, user=None, at_time=None):
		finished_time = at_time or timezone.now()
		self.finished_at = finished_time
		self.finished_by = user
		self.release_at = finished_time
		self.save(update_fields=["finished_at", "finished_by", "release_at", "expected_end_at", "updated_at"])

	def __str__(self):
		return f"Operation #{self.id} - {self.operation_name} ({self.doctor.user.email})"


class MedicalDocumentRequest(models.Model):
	class RequestType(models.TextChoices):
		ANALYSIS = "analysis", "Analysis"
		IMAGING = "imaging", "Imaging"
		DOCUMENT = "document", "Document"
		OTHER = "other", "Other"

	class Status(models.TextChoices):
		PENDING = "pending", "Pending"
		UPLOADED = "uploaded", "Uploaded"
		REVIEWED = "reviewed", "Reviewed"
		CANCELLED = "cancelled", "Cancelled"

	medical_record = models.ForeignKey(
		MedicalRecord,
		on_delete=models.CASCADE,
		related_name="document_requests",
	)
	doctor = models.ForeignKey(
		"doctors.DoctorProfile",
		on_delete=models.CASCADE,
		related_name="document_requests",
	)
	request_type = models.CharField(max_length=20, choices=RequestType.choices, default=RequestType.DOCUMENT)
	title = models.CharField(max_length=180)
	description = models.TextField(blank=True)
	requested_items = models.JSONField(default=list, blank=True)
	due_date = models.DateField(null=True, blank=True)
	status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
	review_note = models.TextField(blank=True)
	closed_at = models.DateTimeField(null=True, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ["-created_at"]

	def __str__(self):
		return f"DocumentRequest #{self.id} for record #{self.medical_record_id}"


class MedicalDocument(models.Model):
	class DocumentType(models.TextChoices):
		ANALYSIS_REPORT = "analysis_report", "Analysis Report"
		IMAGING_RESULT = "imaging_result", "Imaging Result"
		ADMINISTRATIVE = "administrative", "Administrative"
		OTHER = "other", "Other"

	class ReviewStatus(models.TextChoices):
		UPLOADED = "uploaded", "Uploaded"
		REVIEWED = "reviewed", "Reviewed"
		REJECTED = "rejected", "Rejected"

	medical_record = models.ForeignKey(
		MedicalRecord,
		on_delete=models.CASCADE,
		related_name="documents",
	)
	request = models.ForeignKey(
		MedicalDocumentRequest,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name="documents",
	)
	uploaded_by_patient = models.ForeignKey(
		"patients.PatientProfile",
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name="uploaded_medical_documents",
	)
	uploaded_by_doctor = models.ForeignKey(
		"doctors.DoctorProfile",
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name="uploaded_medical_documents",
	)
	document_type = models.CharField(max_length=30, choices=DocumentType.choices, default=DocumentType.OTHER)
	title = models.CharField(max_length=180)
	notes = models.TextField(blank=True)
	file = models.FileField(upload_to="medical_documents/%Y/%m/%d/")
	review_status = models.CharField(max_length=20, choices=ReviewStatus.choices, default=ReviewStatus.UPLOADED)
	reviewed_by = models.ForeignKey(
		"doctors.DoctorProfile",
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name="reviewed_medical_documents",
	)
	review_note = models.TextField(blank=True)
	uploaded_at = models.DateTimeField(auto_now_add=True)
	reviewed_at = models.DateTimeField(null=True, blank=True)

	class Meta:
		ordering = ["-uploaded_at"]

	def __str__(self):
		return f"MedicalDocument #{self.id} for record #{self.medical_record_id}"

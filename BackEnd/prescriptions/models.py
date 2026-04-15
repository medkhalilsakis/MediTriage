from django.db import models


class Prescription(models.Model):
	consultation = models.OneToOneField(
		"medical_records.Consultation",
		on_delete=models.CASCADE,
		related_name="prescription",
	)
	doctor = models.ForeignKey(
		"doctors.DoctorProfile",
		on_delete=models.CASCADE,
		related_name="prescriptions",
	)
	patient = models.ForeignKey(
		"patients.PatientProfile",
		on_delete=models.CASCADE,
		related_name="prescriptions",
	)
	notes = models.TextField(blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ["-created_at"]

	def __str__(self):
		return f"Prescription #{self.id}"


class PrescriptionItem(models.Model):
	prescription = models.ForeignKey(
		Prescription,
		on_delete=models.CASCADE,
		related_name="items",
	)
	medication = models.CharField(max_length=150)
	dosage = models.CharField(max_length=80)
	frequency = models.CharField(max_length=80)
	duration = models.CharField(max_length=80)
	instructions = models.TextField(blank=True)

	def __str__(self):
		return f"{self.medication} ({self.dosage})"

from django.db import models


class FollowUp(models.Model):
	class Status(models.TextChoices):
		SCHEDULED = "scheduled", "Scheduled"
		IN_PROGRESS = "in_progress", "In Progress"
		COMPLETED = "completed", "Completed"
		MISSED = "missed", "Missed"

	patient = models.ForeignKey(
		"patients.PatientProfile",
		on_delete=models.CASCADE,
		related_name="follow_ups",
	)
	doctor = models.ForeignKey(
		"doctors.DoctorProfile",
		on_delete=models.CASCADE,
		related_name="follow_ups",
	)
	consultation = models.ForeignKey(
		"medical_records.Consultation",
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name="follow_ups",
	)
	notes = models.TextField(blank=True)
	scheduled_at = models.DateTimeField()
	status = models.CharField(max_length=20, choices=Status.choices, default=Status.SCHEDULED)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ["scheduled_at"]

	def __str__(self):
		return f"FollowUp #{self.id} - {self.patient.user.email}"


class FollowUpAlert(models.Model):
	class Type(models.TextChoices):
		SMS = "sms", "SMS"
		EMAIL = "email", "Email"
		PUSH = "push", "Push"

	class Status(models.TextChoices):
		PENDING = "pending", "Pending"
		SENT = "sent", "Sent"
		FAILED = "failed", "Failed"

	follow_up = models.ForeignKey(
		FollowUp,
		on_delete=models.CASCADE,
		related_name="alerts",
	)
	alert_type = models.CharField(max_length=10, choices=Type.choices)
	scheduled_at = models.DateTimeField()
	status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
	message = models.TextField(blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ["scheduled_at"]

	def __str__(self):
		return f"Alert #{self.id} ({self.alert_type})"

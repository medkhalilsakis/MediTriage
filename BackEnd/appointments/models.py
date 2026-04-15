from django.db import models
from django.db.models import Q


class Appointment(models.Model):
	class Department(models.TextChoices):
		CARDIOLOGY = "cardiology", "Departement de cardiologie"
		RESPIRATORY = "respiratory", "Departement des maladies respiratoires"
		NEUROLOGY = "neurology", "Departement de neurologie"
		GASTROENTEROLOGY = "gastroenterology", "Departement de gastroenterologie"
		DERMATOLOGY = "dermatology", "Departement de dermatologie"
		ENDOCRINOLOGY = "endocrinology", "Departement d'endocrinologie"
		GENERAL_MEDICINE = "general_medicine", "Departement de medecine generale"

	class Status(models.TextChoices):
		PENDING = "pending", "Pending"
		CONFIRMED = "confirmed", "Confirmed"
		COMPLETED = "completed", "Completed"
		CANCELLED = "cancelled", "Cancelled"
		NO_SHOW = "no_show", "No Show"

	class UrgencyLevel(models.TextChoices):
		LOW = "low", "Low"
		MEDIUM = "medium", "Medium"
		HIGH = "high", "High"
		CRITICAL = "critical", "Critical"

	patient = models.ForeignKey(
		"patients.PatientProfile",
		on_delete=models.CASCADE,
		related_name="appointments",
	)
	doctor = models.ForeignKey(
		"doctors.DoctorProfile",
		on_delete=models.CASCADE,
		related_name="appointments",
	)
	scheduled_at = models.DateTimeField()
	status = models.CharField(max_length=20, choices=Status.choices, default=Status.CONFIRMED)
	urgency_level = models.CharField(
		max_length=20,
		choices=UrgencyLevel.choices,
		default=UrgencyLevel.MEDIUM,
	)
	department = models.CharField(
		max_length=40,
		choices=Department.choices,
		default=Department.GENERAL_MEDICINE,
	)
	reason = models.TextField(blank=True)
	notes = models.TextField(blank=True)
	last_staff_action_at = models.DateTimeField(null=True, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ["-scheduled_at"]

	def __str__(self):
		return f"Appointment #{self.id} - {self.patient.user.email} with {self.doctor.user.email}"


class AppointmentAdvanceOffer(models.Model):
	class Status(models.TextChoices):
		PENDING = "pending", "Pending"
		ACCEPTED = "accepted", "Accepted"
		REJECTED = "rejected", "Rejected"
		EXPIRED = "expired", "Expired"

	appointment = models.ForeignKey(
		Appointment,
		on_delete=models.CASCADE,
		related_name="advance_offers",
	)
	offered_doctor = models.ForeignKey(
		"doctors.DoctorProfile",
		on_delete=models.CASCADE,
		related_name="received_advance_offers",
	)
	offered_slot = models.DateTimeField()
	status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
	expires_at = models.DateTimeField()
	requested_by = models.ForeignKey(
		"authentication.CustomUser",
		null=True,
		blank=True,
		on_delete=models.SET_NULL,
		related_name="appointment_advance_offers",
	)
	responded_at = models.DateTimeField(null=True, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ["-created_at"]
		constraints = [
			models.UniqueConstraint(
				fields=["appointment"],
				condition=Q(status="pending"),
				name="unique_pending_offer_per_appointment",
			)
		]

	def __str__(self):
		return (
			f"AdvanceOffer #{self.id} for appointment {self.appointment_id} "
			f"at {self.offered_slot} ({self.status})"
		)

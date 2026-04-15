from django.conf import settings
from django.db import models
from django.db.models import F, Q


class DoctorProfile(models.Model):
	class Department(models.TextChoices):
		CARDIOLOGY = "cardiology", "Departement de cardiologie"
		RESPIRATORY = "respiratory", "Departement des maladies respiratoires"
		NEUROLOGY = "neurology", "Departement de neurologie"
		GASTROENTEROLOGY = "gastroenterology", "Departement de gastroenterologie"
		DERMATOLOGY = "dermatology", "Departement de dermatologie"
		ENDOCRINOLOGY = "endocrinology", "Departement d'endocrinologie"
		GENERAL_MEDICINE = "general_medicine", "Departement de medecine generale"

	user = models.OneToOneField(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name="doctor_profile",
	)
	specialization = models.CharField(max_length=120)
	department = models.CharField(
		max_length=40,
		choices=Department.choices,
		default=Department.GENERAL_MEDICINE,
	)
	license_number = models.CharField(max_length=80, unique=True)
	years_of_experience = models.PositiveIntegerField(default=0)
	consultation_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
	bio = models.TextField(blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	def __str__(self):
		return f"Dr. {self.user.get_full_name() or self.user.email} - {self.specialization}"


class DoctorAvailabilitySlot(models.Model):
	class WeekDay(models.IntegerChoices):
		MONDAY = 0, "Monday"
		TUESDAY = 1, "Tuesday"
		WEDNESDAY = 2, "Wednesday"
		THURSDAY = 3, "Thursday"
		FRIDAY = 4, "Friday"
		SATURDAY = 5, "Saturday"
		SUNDAY = 6, "Sunday"

	doctor = models.ForeignKey(
		DoctorProfile,
		on_delete=models.CASCADE,
		related_name="availability_slots",
	)
	weekday = models.IntegerField(choices=WeekDay.choices)
	start_time = models.TimeField()
	end_time = models.TimeField()
	is_active = models.BooleanField(default=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ["weekday", "start_time"]
		unique_together = ("doctor", "weekday", "start_time", "end_time")

	def __str__(self):
		return f"{self.doctor.user.email} - {self.get_weekday_display()} {self.start_time}-{self.end_time}"


class DoctorLeave(models.Model):
	class Status(models.TextChoices):
		PENDING = "pending", "Pending"
		APPROVED = "approved", "Approved"
		REJECTED = "rejected", "Rejected"
		CANCELLED = "cancelled", "Cancelled"

	doctor = models.ForeignKey(
		DoctorProfile,
		on_delete=models.CASCADE,
		related_name="leave_periods",
	)
	start_date = models.DateField()
	end_date = models.DateField()
	reason = models.TextField(blank=True)
	status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
	is_active = models.BooleanField(default=False)
	created_by = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		null=True,
		blank=True,
		on_delete=models.SET_NULL,
		related_name="doctor_leave_requests",
	)
	reviewed_by = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		null=True,
		blank=True,
		on_delete=models.SET_NULL,
		related_name="reviewed_doctor_leave_requests",
	)
	reviewed_at = models.DateTimeField(null=True, blank=True)
	review_note = models.TextField(blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ["-start_date", "-created_at"]
		constraints = [
			models.CheckConstraint(
				condition=Q(end_date__gte=F("start_date")),
				name="doctor_leave_end_after_start",
			)
		]

	def __str__(self):
		return f"{self.doctor.user.email} leave {self.start_date} -> {self.end_date} ({self.status})"

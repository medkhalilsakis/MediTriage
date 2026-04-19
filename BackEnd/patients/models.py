from django.conf import settings
from django.db import models


class PatientProfile(models.Model):
	DELETED_USER_LABEL = "deleted user"

	class Gender(models.TextChoices):
		MALE = "male", "Male"
		FEMALE = "female", "Female"
		OTHER = "other", "Other"

	class BloodGroup(models.TextChoices):
		A_POS = "A+", "A+"
		A_NEG = "A-", "A-"
		B_POS = "B+", "B+"
		B_NEG = "B-", "B-"
		AB_POS = "AB+", "AB+"
		AB_NEG = "AB-", "AB-"
		O_POS = "O+", "O+"
		O_NEG = "O-", "O-"

	user = models.OneToOneField(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name="patient_profile",
	)
	dob = models.DateField(null=True, blank=True)
	gender = models.CharField(max_length=10, choices=Gender.choices, blank=True)
	blood_group = models.CharField(max_length=3, choices=BloodGroup.choices, blank=True)
	allergies = models.TextField(blank=True)
	emergency_contact_name = models.CharField(max_length=120, blank=True)
	emergency_contact_phone = models.CharField(max_length=20, blank=True)
	address = models.TextField(blank=True)
	is_account_deleted = models.BooleanField(default=False)
	account_deleted_at = models.DateTimeField(null=True, blank=True)
	deleted_by = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name="deleted_patient_profiles",
	)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	def get_public_identity_label(self):
		if self.is_account_deleted:
			return self.DELETED_USER_LABEL

		user = getattr(self, 'user', None)
		email = getattr(user, 'email', '') if user else ''
		return email or self.DELETED_USER_LABEL

	def __str__(self):
		return f"PatientProfile<{self.user.email}>"

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class CustomUserManager(BaseUserManager):
	"""Custom manager to enforce email presence and normalize identity fields."""

	def create_user(self, email, password=None, **extra_fields):
		if not email:
			raise ValueError("Users must have an email address")

		email = self.normalize_email(email)
		username = extra_fields.get("username")

		if not username:
			username = email.split("@")[0]
			extra_fields["username"] = username

		user = self.model(email=email, **extra_fields)
		user.set_password(password)
		user.save(using=self._db)
		return user

	def create_superuser(self, email, password=None, **extra_fields):
		extra_fields.setdefault("is_staff", True)
		extra_fields.setdefault("is_superuser", True)
		extra_fields.setdefault("is_active", True)
		extra_fields.setdefault("role", CustomUser.Role.ADMIN)

		if extra_fields.get("is_staff") is not True:
			raise ValueError("Superuser must have is_staff=True.")
		if extra_fields.get("is_superuser") is not True:
			raise ValueError("Superuser must have is_superuser=True.")

		return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractUser):
	class Role(models.TextChoices):
		PATIENT = "patient", "Patient"
		DOCTOR = "doctor", "Doctor"
		ADMIN = "admin", "Admin"

	email = models.EmailField(unique=True)
	role = models.CharField(max_length=20, choices=Role.choices, default=Role.PATIENT)
	phone_number = models.CharField(max_length=20, blank=True)
	profile_image = models.FileField(upload_to='profile_images/%Y/%m/', blank=True, null=True)
	is_verified = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	USERNAME_FIELD = "email"
	REQUIRED_FIELDS = ["username"]

	objects = CustomUserManager()

	def __str__(self):
		return f"{self.email} ({self.role})"

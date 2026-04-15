from django.db import models


class ChatbotSession(models.Model):
	patient = models.ForeignKey(
		"patients.PatientProfile",
		on_delete=models.CASCADE,
		related_name="chatbot_sessions",
	)
	title = models.CharField(max_length=120, blank=True)
	booked_appointment = models.OneToOneField(
		"appointments.Appointment",
		null=True,
		blank=True,
		on_delete=models.SET_NULL,
		related_name="chatbot_session",
	)
	awaiting_appointment_confirmation = models.BooleanField(default=False)
	latest_analysis = models.JSONField(default=dict, blank=True)
	is_closed = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ["-updated_at"]

	def __str__(self):
		return f"ChatSession #{self.id} - {self.patient.user.email}"


class ChatbotMessage(models.Model):
	class Sender(models.TextChoices):
		PATIENT = "patient", "Patient"
		BOT = "bot", "Bot"

	session = models.ForeignKey(
		ChatbotSession,
		on_delete=models.CASCADE,
		related_name="messages",
	)
	sender = models.CharField(max_length=10, choices=Sender.choices)
	content = models.TextField()
	metadata = models.JSONField(default=dict, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ["created_at"]

	def __str__(self):
		return f"{self.sender} message #{self.id}"

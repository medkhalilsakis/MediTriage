from django.db import models


class Notification(models.Model):
	class Type(models.TextChoices):
		SYSTEM = "system", "System"
		APPOINTMENT = "appointment", "Appointment"
		PRESCRIPTION = "prescription", "Prescription"
		FOLLOW_UP = "follow_up", "Follow-up"
		CHATBOT = "chatbot", "Chatbot"

	recipient = models.ForeignKey(
		"authentication.CustomUser",
		on_delete=models.CASCADE,
		related_name="notifications",
	)
	notification_type = models.CharField(max_length=20, choices=Type.choices)
	title = models.CharField(max_length=120)
	message = models.TextField()
	is_read = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ["-created_at"]

	def __str__(self):
		return f"Notification #{self.id} to {self.recipient.email}"

from django.conf import settings
from django.db import models
from django.utils import timezone


class Conversation(models.Model):
    participant_low = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='messaging_conversations_low',
    )
    participant_high = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='messaging_conversations_high',
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='messaging_conversations_created',
    )
    last_message_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-last_message_at', '-updated_at']
        constraints = [
            models.UniqueConstraint(
                fields=['participant_low', 'participant_high'],
                name='messaging_unique_participant_pair',
            ),
            models.CheckConstraint(
                condition=~models.Q(participant_low=models.F('participant_high')),
                name='messaging_distinct_participants',
            ),
        ]

    def touch_last_message(self):
        self.last_message_at = timezone.now()
        self.save(update_fields=['last_message_at', 'updated_at'])

    def __str__(self):
        return f"Conversation #{self.id}: {self.participant_low.email} <-> {self.participant_high.email}"


class DirectMessage(models.Model):
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages',
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='messaging_sent_messages',
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='messaging_received_messages',
    )
    content = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['conversation', 'created_at']),
            models.Index(fields=['recipient', 'is_read']),
        ]

    def __str__(self):
        return f"Message #{self.id} in conversation #{self.conversation_id}"


class UserPresence(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='presence',
    )
    is_online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-last_seen']

    def __str__(self):
        state = 'online' if self.is_online else 'offline'
        return f"{self.user.email} ({state})"

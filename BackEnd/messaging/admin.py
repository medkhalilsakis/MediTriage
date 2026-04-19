from django.contrib import admin

from .models import Conversation, DirectMessage, UserPresence


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('id', 'participant_low', 'participant_high', 'last_message_at', 'updated_at')
    search_fields = ('participant_low__email', 'participant_high__email')
    ordering = ('-last_message_at', '-updated_at')


@admin.register(DirectMessage)
class DirectMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'conversation', 'sender', 'recipient', 'is_read', 'created_at')
    search_fields = ('sender__email', 'recipient__email', 'content')
    ordering = ('-created_at',)


@admin.register(UserPresence)
class UserPresenceAdmin(admin.ModelAdmin):
    list_display = ('user', 'is_online', 'last_seen', 'updated_at')
    search_fields = ('user__email',)
    ordering = ('-last_seen',)

from django.contrib import admin

from .models import ChatbotMessage, ChatbotSession


@admin.register(ChatbotSession)
class ChatbotSessionAdmin(admin.ModelAdmin):
	list_display = ('id', 'patient', 'is_closed', 'created_at', 'updated_at')
	search_fields = ('patient__user__email', 'title')


@admin.register(ChatbotMessage)
class ChatbotMessageAdmin(admin.ModelAdmin):
	list_display = ('id', 'session', 'sender', 'created_at')
	search_fields = ('content',)

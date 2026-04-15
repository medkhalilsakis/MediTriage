from django.contrib import admin

from .models import FollowUp, FollowUpAlert


@admin.register(FollowUp)
class FollowUpAdmin(admin.ModelAdmin):
	list_display = ('id', 'patient', 'doctor', 'scheduled_at', 'status')
	list_filter = ('status',)


@admin.register(FollowUpAlert)
class FollowUpAlertAdmin(admin.ModelAdmin):
	list_display = ('id', 'follow_up', 'alert_type', 'scheduled_at', 'status')
	list_filter = ('alert_type', 'status')

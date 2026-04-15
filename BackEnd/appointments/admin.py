from django.contrib import admin

from .models import Appointment, AppointmentAdvanceOffer


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
	list_display = ('id', 'patient', 'doctor', 'department', 'scheduled_at', 'status', 'urgency_level')
	list_filter = ('department', 'status', 'urgency_level')
	search_fields = ('patient__user__email', 'doctor__user__email')


@admin.register(AppointmentAdvanceOffer)
class AppointmentAdvanceOfferAdmin(admin.ModelAdmin):
	list_display = ('id', 'appointment', 'offered_doctor', 'offered_slot', 'status', 'expires_at')
	list_filter = ('status', 'offered_slot')
	search_fields = ('appointment__patient__user__email', 'offered_doctor__user__email')

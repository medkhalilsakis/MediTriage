from django.contrib import admin

from .models import DoctorAvailabilitySlot, DoctorLeave, DoctorProfile


@admin.register(DoctorProfile)
class DoctorProfileAdmin(admin.ModelAdmin):
	list_display = ('id', 'user', 'specialization', 'department', 'license_number', 'years_of_experience')
	list_filter = ('department',)
	search_fields = ('user__email', 'specialization', 'department', 'license_number')


@admin.register(DoctorAvailabilitySlot)
class DoctorAvailabilitySlotAdmin(admin.ModelAdmin):
	list_display = ('id', 'doctor', 'weekday', 'start_time', 'end_time', 'is_active')
	list_filter = ('weekday', 'is_active')


@admin.register(DoctorLeave)
class DoctorLeaveAdmin(admin.ModelAdmin):
	list_display = ('id', 'doctor', 'start_date', 'end_date', 'status', 'is_active', 'created_by', 'reviewed_by')
	list_filter = ('status', 'is_active', 'start_date', 'end_date')
	search_fields = ('doctor__user__email', 'reason', 'created_by__email', 'reviewed_by__email')

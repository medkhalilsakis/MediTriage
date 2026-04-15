from django.contrib import admin

from .models import Prescription, PrescriptionItem


class PrescriptionItemInline(admin.TabularInline):
	model = PrescriptionItem
	extra = 0


@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
	list_display = ('id', 'patient', 'doctor', 'created_at')
	search_fields = ('patient__user__email', 'doctor__user__email')
	inlines = [PrescriptionItemInline]

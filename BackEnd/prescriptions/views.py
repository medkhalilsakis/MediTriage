from io import BytesIO

from django.http import HttpResponse
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from rest_framework import permissions, viewsets
from rest_framework.decorators import action

from .models import Prescription
from .serializers import PrescriptionSerializer


class PrescriptionViewSet(viewsets.ModelViewSet):
	serializer_class = PrescriptionSerializer
	queryset = Prescription.objects.select_related(
		'consultation', 'doctor__user', 'patient__user'
	).prefetch_related('items').all()
	filterset_fields = ['doctor', 'patient', 'consultation']
	search_fields = ['patient__user__email', 'doctor__user__email', 'notes', 'items__medication']
	ordering_fields = ['created_at', 'updated_at']

	def get_permissions(self):
		return [permissions.IsAuthenticated()]

	def get_queryset(self):
		user = self.request.user
		qs = self.queryset
		if user.role == 'patient':
			return qs.filter(patient__user=user)
		if user.role == 'doctor':
			return qs.filter(doctor__user=user)
		return qs

	@action(detail=True, methods=['get'], url_path='pdf')
	def pdf(self, request, pk=None):
		prescription = self.get_object()

		buffer = BytesIO()
		p = canvas.Canvas(buffer, pagesize=A4)
		width, height = A4
		y = height - 50

		p.setFont('Helvetica-Bold', 16)
		p.drawString(50, y, f'Prescription #{prescription.id}')
		y -= 30

		p.setFont('Helvetica', 11)
		p.drawString(50, y, f'Doctor: {prescription.doctor.user.get_full_name() or prescription.doctor.user.email}')
		y -= 20
		p.drawString(50, y, f'Patient: {prescription.patient.user.get_full_name() or prescription.patient.user.email}')
		y -= 20
		p.drawString(50, y, f'Date: {prescription.created_at.strftime("%Y-%m-%d %H:%M")}')
		y -= 30

		p.setFont('Helvetica-Bold', 12)
		p.drawString(50, y, 'Medications')
		y -= 20

		p.setFont('Helvetica', 10)
		for index, item in enumerate(prescription.items.all(), start=1):
			line = f"{index}. {item.medication} | {item.dosage} | {item.frequency} | {item.duration}"
			p.drawString(50, y, line[:120])
			y -= 16
			if item.instructions:
				p.drawString(70, y, f"Instructions: {item.instructions[:100]}")
				y -= 16
			if y < 80:
				p.showPage()
				y = height - 50

		if prescription.notes:
			y -= 10
			p.setFont('Helvetica-Bold', 11)
			p.drawString(50, y, 'Notes:')
			y -= 16
			p.setFont('Helvetica', 10)
			p.drawString(50, y, prescription.notes[:140])

		p.showPage()
		p.save()
		buffer.seek(0)

		response = HttpResponse(buffer, content_type='application/pdf')
		response['Content-Disposition'] = f'attachment; filename="prescription_{prescription.id}.pdf"'
		return response

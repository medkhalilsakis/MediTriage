from datetime import timedelta

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from appointments.models import Appointment
from appointments.scheduling import DEFAULT_END_TIME, DEFAULT_START_TIME, is_doctor_available_for_slot, normalize_slot_datetime
from appointments.serializers import AppointmentSerializer
from chatbot.models import ChatbotMessage
from doctors.models import DoctorProfile
from follow_up.models import FollowUp
from follow_up.serializers import FollowUpSerializer
from notifications.models import Notification
from patients.models import PatientProfile

from .models import Consultation, MedicalDocument, MedicalDocumentRequest, MedicalRecord
from .serializers import (
	ConsultationSerializer,
	MedicalDocumentRequestSerializer,
	MedicalDocumentSerializer,
	MedicalRecordSerializer,
)


class MedicalRecordViewSet(viewsets.ModelViewSet):
	serializer_class = MedicalRecordSerializer
	queryset = MedicalRecord.objects.select_related('patient__user', 'archived_by').prefetch_related(
		'consultations__doctor__user',
		'document_requests__doctor__user',
		'documents',
	).all()
	filterset_fields = ['patient', 'status']
	search_fields = ['patient__user__email', 'chronic_conditions', 'family_history', 'consultation_motive', 'diagnostic_summary']
	ordering_fields = ['created_at', 'updated_at']

	def get_permissions(self):
		return [permissions.IsAuthenticated()]

	def get_queryset(self):
		user = self.request.user
		qs = self.queryset
		if user.role == 'patient':
			return qs.filter(patient__user=user)
		if user.role == 'doctor':
			return qs.filter(
				Q(consultations__doctor__user=user)
				| Q(document_requests__doctor__user=user)
				| Q(documents__uploaded_by_doctor__user=user)
				| Q(documents__reviewed_by__user=user)
			).distinct()
		return qs

	def perform_create(self, serializer):
		user = self.request.user
		if user.role not in ['doctor', 'admin']:
			raise PermissionDenied('Only doctors and admins can create medical records.')

		record = serializer.save()
		self._populate_administrative_snapshot(record)

	def perform_update(self, serializer):
		user = self.request.user
		record = serializer.instance
		if user.role == 'patient':
			raise PermissionDenied('Patients cannot edit medical records directly.')
		if user.role == 'doctor':
			doctor_profile = self._get_doctor_profile(user)
			self._ensure_doctor_can_manage_record(doctor_profile, record)

		updated = serializer.save()
		self._populate_administrative_snapshot(updated)

	def perform_destroy(self, instance):
		user = self.request.user
		if user.role not in ['doctor', 'admin']:
			raise PermissionDenied('Only doctors and admins can delete medical records.')
		if user.role == 'doctor':
			doctor_profile = self._get_doctor_profile(user)
			self._ensure_doctor_can_manage_record(doctor_profile, instance)
		instance.delete()

	@action(detail=True, methods=['post'], url_path='close')
	def close(self, request, pk=None):
		record = self.get_object()
		self._ensure_staff_record_access(record, request.user)

		record.status = MedicalRecord.Status.CLOSED
		record.closed_at = timezone.now()
		record.save(update_fields=['status', 'closed_at', 'updated_at'])

		self._notify_record_update(record, 'Medical record closed', 'Your medical record was marked as closed.')
		return Response(self.get_serializer(record).data)

	@action(detail=True, methods=['post'], url_path='archive')
	def archive(self, request, pk=None):
		record = self.get_object()
		self._ensure_staff_record_access(record, request.user)

		record.status = MedicalRecord.Status.ARCHIVED
		now = timezone.now()
		record.archived_at = now
		record.closed_at = record.closed_at or now
		record.archived_by = request.user
		record.save(update_fields=['status', 'archived_at', 'closed_at', 'archived_by', 'updated_at'])

		self._notify_record_update(record, 'Medical record archived', 'Your medical record has been archived by your doctor.')
		return Response(self.get_serializer(record).data)

	@action(detail=True, methods=['post'], url_path='reopen')
	def reopen(self, request, pk=None):
		record = self.get_object()
		self._ensure_staff_record_access(record, request.user)

		record.status = MedicalRecord.Status.ACTIVE
		record.closed_at = None
		record.archived_at = None
		record.archived_by = None
		record.save(update_fields=['status', 'closed_at', 'archived_at', 'archived_by', 'updated_at'])

		self._notify_record_update(record, 'Medical record reopened', 'Your medical record has been reopened for follow-up care.')
		return Response(self.get_serializer(record).data)

	def _ensure_staff_record_access(self, record, user):
		if user.role not in ['doctor', 'admin']:
			raise PermissionDenied('Only doctor or admin can update medical record lifecycle.')
		if user.role == 'doctor':
			doctor_profile = self._get_doctor_profile(user)
			self._ensure_doctor_can_manage_record(doctor_profile, record)

	@staticmethod
	def _get_doctor_profile(user):
		doctor_profile = DoctorProfile.objects.filter(user=user).first()
		if not doctor_profile:
			raise ValidationError({'doctor': 'Doctor profile is missing for this account.'})
		return doctor_profile

	@staticmethod
	def _ensure_doctor_can_manage_record(doctor_profile, record):
		has_consultation = Consultation.objects.filter(medical_record=record, doctor=doctor_profile).exists()
		if not has_consultation:
			raise PermissionDenied('You can only manage records linked to your own consultations.')

	@staticmethod
	def _populate_administrative_snapshot(record):
		patient = record.patient
		user = patient.user
		full_name = f"{(user.first_name or '').strip()} {(user.last_name or '').strip()}".strip()

		changed = False
		updates = {}
		if not record.patient_full_name and full_name:
			updates['patient_full_name'] = full_name
			changed = True
		if not record.patient_date_of_birth and patient.dob:
			updates['patient_date_of_birth'] = patient.dob
			changed = True
		if not record.patient_gender and patient.gender:
			updates['patient_gender'] = patient.gender
			changed = True
		if not record.patient_phone and user.phone_number:
			updates['patient_phone'] = user.phone_number
			changed = True
		if not record.patient_address and patient.address:
			updates['patient_address'] = patient.address
			changed = True
		if not record.emergency_contact_name and patient.emergency_contact_name:
			updates['emergency_contact_name'] = patient.emergency_contact_name
			changed = True
		if not record.emergency_contact_phone and patient.emergency_contact_phone:
			updates['emergency_contact_phone'] = patient.emergency_contact_phone
			changed = True

		if changed:
			for key, value in updates.items():
				setattr(record, key, value)
			record.save(update_fields=[*updates.keys(), 'updated_at'])

	@staticmethod
	def _notify_record_update(record, title, message):
		Notification.objects.create(
			recipient=record.patient.user,
			notification_type=Notification.Type.FOLLOW_UP,
			title=title,
			message=message,
		)


class ConsultationViewSet(viewsets.ModelViewSet):
	serializer_class = ConsultationSerializer
	queryset = Consultation.objects.select_related(
		'medical_record__patient__user',
		'doctor__user',
		'appointment',
	).all()
	filterset_fields = ['medical_record', 'doctor', 'appointment', 'icd10_code']
	search_fields = ['diagnosis', 'anamnesis', 'icd10_code', 'treatment_plan']
	ordering_fields = ['created_at', 'updated_at']

	def get_permissions(self):
		return [permissions.IsAuthenticated()]

	def get_queryset(self):
		user = self.request.user
		qs = self.queryset
		if user.role == 'patient':
			return qs.filter(medical_record__patient__user=user)
		if user.role == 'doctor':
			return qs.filter(doctor__user=user)
		return qs

	def perform_create(self, serializer):
		user = self.request.user
		if user.role not in ['doctor', 'admin']:
			raise PermissionDenied('Only doctor or admin can create consultations.')

		if user.role == 'doctor':
			doctor_profile = DoctorProfile.objects.filter(user=user).first()
			if not doctor_profile:
				raise ValidationError({'doctor': 'Doctor profile is missing for this account.'})
		else:
			doctor_profile = serializer.validated_data.get('doctor')
			if not doctor_profile:
				raise ValidationError({'doctor': 'This field is required.'})

		medical_record = serializer.validated_data.get('medical_record')
		appointment = serializer.validated_data.get('appointment')

		if appointment:
			if appointment.doctor_id != doctor_profile.id:
				raise ValidationError({'appointment': 'Appointment is not assigned to this doctor.'})
			if medical_record.patient_id != appointment.patient_id:
				raise ValidationError({'medical_record': 'Medical record patient must match appointment patient.'})

		serializer.save(doctor=doctor_profile)

	@action(detail=False, methods=['post'], url_path='create-from-appointment')
	def create_from_appointment(self, request):
		if request.user.role != 'doctor':
			raise PermissionDenied('Only doctors can create consultation records from daily schedule.')

		doctor_profile = DoctorProfile.objects.select_related('user').filter(user=request.user).first()
		if not doctor_profile:
			raise ValidationError({'doctor': 'Doctor profile is missing for this account.'})

		appointment_id = request.data.get('appointment_id') or request.data.get('appointment')
		if not appointment_id:
			raise ValidationError({'appointment_id': 'This field is required.'})

		try:
			appointment = Appointment.objects.select_related('patient__user', 'doctor__user').get(pk=appointment_id)
		except Appointment.DoesNotExist as exc:
			raise ValidationError({'appointment_id': 'Appointment not found.'}) from exc

		if appointment.doctor_id != doctor_profile.id:
			raise PermissionDenied('You can only create records for your own scheduled patients.')

		diagnosis = str(request.data.get('diagnosis', '') or '').strip()
		if not diagnosis:
			raise ValidationError({'diagnosis': 'Doctor diagnosis is required.'})

		vitals = request.data.get('vitals')
		if vitals in [None, '']:
			vitals = {}
		if not isinstance(vitals, dict):
			raise ValidationError({'vitals': 'Vitals must be a JSON object.'})

		anamnesis = str(request.data.get('anamnesis', '') or '').strip()
		icd10_code = str(request.data.get('icd10_code', '') or '').strip()
		treatment_plan = str(request.data.get('treatment_plan', '') or '').strip()

		with transaction.atomic():
			medical_record, _ = MedicalRecord.objects.get_or_create(patient=appointment.patient)
			MedicalRecordViewSet._populate_administrative_snapshot(medical_record)

			existing = Consultation.objects.filter(appointment=appointment).first()
			if existing:
				return Response(
					{
						'created': False,
						'medical_record': MedicalRecordSerializer(medical_record, context={'request': request}).data,
						'consultation': ConsultationSerializer(existing, context={'request': request}).data,
					},
					status=status.HTTP_200_OK,
				)

			chatbot_diagnosis = self._extract_chatbot_diagnosis_for_appointment(appointment)
			self._update_record_sections_from_payload(
				medical_record=medical_record,
				appointment=appointment,
				diagnosis=diagnosis,
				anamnesis=anamnesis,
				treatment_plan=treatment_plan,
				payload=request.data,
			)

			consultation = Consultation.objects.create(
				medical_record=medical_record,
				appointment=appointment,
				doctor=doctor_profile,
				chatbot_diagnosis=chatbot_diagnosis,
				diagnosis=diagnosis,
				vitals=vitals,
				anamnesis=anamnesis,
				icd10_code=icd10_code,
				treatment_plan=treatment_plan,
			)

			appointment.status = Appointment.Status.COMPLETED
			appointment.last_staff_action_at = timezone.now()
			appointment.notes = self._append_note(
				appointment.notes,
				f"Medical record consultation #{consultation.id} created by Dr. {doctor_profile.user.email}.",
			)
			appointment.save(update_fields=['status', 'last_staff_action_at', 'notes', 'updated_at'])

		return Response(
			{
				'created': True,
				'medical_record': MedicalRecordSerializer(medical_record, context={'request': request}).data,
				'consultation': ConsultationSerializer(consultation, context={'request': request}).data,
			},
			status=status.HTTP_201_CREATED,
		)

	@action(detail=True, methods=['post'], url_path='schedule-follow-up')
	def schedule_follow_up(self, request, pk=None):
		consultation = self.get_object()
		user = request.user

		if user.role not in ['doctor', 'admin']:
			raise PermissionDenied('Only doctor or admin can schedule follow-up appointments.')
		if user.role == 'doctor' and consultation.doctor.user_id != user.id:
			raise PermissionDenied('Doctors can only schedule follow-up for their own consultations.')

		raw_scheduled_at = request.data.get('scheduled_at')
		if not raw_scheduled_at:
			raise ValidationError({'scheduled_at': 'This field is required.'})

		slot_serializer = AppointmentSerializer(
			data={'scheduled_at': raw_scheduled_at},
			partial=True,
			context={'request': request},
		)
		slot_serializer.is_valid(raise_exception=True)
		scheduled_at = slot_serializer.validated_data.get('scheduled_at')
		if not scheduled_at:
			raise ValidationError({'scheduled_at': 'Invalid scheduled date.'})
		if scheduled_at <= timezone.now():
			raise ValidationError({'scheduled_at': 'Scheduled date must be in the future.'})

		normalized_slot = normalize_slot_datetime(scheduled_at)
		local_slot = timezone.localtime(scheduled_at).replace(second=0, microsecond=0)
		if normalized_slot != local_slot:
			raise ValidationError({'scheduled_at': 'Follow-up appointment must align with 30-minute slots.'})
		if local_slot.weekday() == 6:
			raise ValidationError({'scheduled_at': 'Appointments cannot be scheduled on Sundays.'})
		if not (DEFAULT_START_TIME <= local_slot.time() < DEFAULT_END_TIME):
			raise ValidationError({'scheduled_at': 'Follow-up must be scheduled between 08:00 and 16:00.'})

		if not is_doctor_available_for_slot(consultation.doctor, normalized_slot):
			raise ValidationError({'scheduled_at': 'Doctor is not available for this follow-up slot.'})

		note = str(request.data.get('notes', '') or '').strip()
		reason = str(request.data.get('reason', '') or '').strip() or 'Follow-up consultation'

		appointment = Appointment.objects.create(
			patient=consultation.medical_record.patient,
			doctor=consultation.doctor,
			scheduled_at=normalized_slot,
			status=Appointment.Status.CONFIRMED,
			urgency_level=Appointment.UrgencyLevel.MEDIUM,
			department=consultation.doctor.department,
			reason=reason,
			notes=note,
			last_staff_action_at=timezone.now(),
		)

		follow_up = FollowUp.objects.create(
			patient=consultation.medical_record.patient,
			doctor=consultation.doctor,
			consultation=consultation,
			notes=note,
			scheduled_at=normalized_slot,
			status=FollowUp.Status.SCHEDULED,
		)

		consultation.medical_record.follow_up_plan = self._append_note(
			consultation.medical_record.follow_up_plan,
			f"Follow-up planned on {timezone.localtime(normalized_slot).strftime('%Y-%m-%d %H:%M')}.",
		)
		consultation.medical_record.save(update_fields=['follow_up_plan', 'updated_at'])

		Notification.objects.create(
			recipient=consultation.medical_record.patient.user,
			notification_type=Notification.Type.FOLLOW_UP,
			title='New follow-up appointment',
			message=(
				f"A follow-up appointment has been scheduled on "
				f"{timezone.localtime(normalized_slot).strftime('%Y-%m-%d %H:%M')} with Dr. {consultation.doctor.user.email}."
			),
		)

		return Response(
			{
				'appointment': AppointmentSerializer(appointment, context={'request': request}).data,
				'follow_up': FollowUpSerializer(follow_up, context={'request': request}).data,
			},
			status=status.HTTP_201_CREATED,
		)

	@action(detail=True, methods=['post'], url_path='refer')
	def refer(self, request, pk=None):
		consultation = self.get_object()
		user = request.user

		if user.role not in ['doctor', 'admin']:
			raise PermissionDenied('Only doctor or admin can create referral appointments.')
		if user.role == 'doctor' and consultation.doctor.user_id != user.id:
			raise PermissionDenied('Doctors can only create referrals from their own consultations.')

		target_doctor_id = request.data.get('target_doctor_id') or request.data.get('doctor_id')
		if not target_doctor_id:
			raise ValidationError({'target_doctor_id': 'This field is required.'})

		try:
			target_doctor = DoctorProfile.objects.select_related('user').get(pk=target_doctor_id)
		except DoctorProfile.DoesNotExist as exc:
			raise ValidationError({'target_doctor_id': 'Target doctor does not exist.'}) from exc

		requested_department = str(request.data.get('department', '') or '').strip()
		if requested_department and requested_department != target_doctor.department:
			raise ValidationError({'department': 'Department must match the selected target doctor.'})

		raw_scheduled_at = request.data.get('scheduled_at')
		if not raw_scheduled_at:
			raise ValidationError({'scheduled_at': 'This field is required.'})

		slot_serializer = AppointmentSerializer(
			data={'scheduled_at': raw_scheduled_at},
			partial=True,
			context={'request': request},
		)
		slot_serializer.is_valid(raise_exception=True)
		scheduled_at = slot_serializer.validated_data.get('scheduled_at')
		if not scheduled_at:
			raise ValidationError({'scheduled_at': 'Invalid scheduled date.'})
		if scheduled_at <= timezone.now():
			raise ValidationError({'scheduled_at': 'Scheduled date must be in the future.'})

		normalized_slot = normalize_slot_datetime(scheduled_at)
		local_slot = timezone.localtime(scheduled_at).replace(second=0, microsecond=0)
		if normalized_slot != local_slot:
			raise ValidationError({'scheduled_at': 'Referral appointment must align with 30-minute slots.'})
		if local_slot.weekday() == 6:
			raise ValidationError({'scheduled_at': 'Appointments cannot be scheduled on Sundays.'})
		if not (DEFAULT_START_TIME <= local_slot.time() < DEFAULT_END_TIME):
			raise ValidationError({'scheduled_at': 'Referral must be scheduled between 08:00 and 16:00.'})

		if not is_doctor_available_for_slot(target_doctor, normalized_slot):
			raise ValidationError({'scheduled_at': 'Target doctor is not available for this slot.'})

		reason = str(request.data.get('reason', '') or '').strip() or 'Referral consultation'
		note = str(request.data.get('notes', '') or '').strip()

		appointment = Appointment.objects.create(
			patient=consultation.medical_record.patient,
			doctor=target_doctor,
			scheduled_at=normalized_slot,
			status=Appointment.Status.CONFIRMED,
			urgency_level=Appointment.UrgencyLevel.MEDIUM,
			department=target_doctor.department,
			reason=reason,
			notes=note,
			last_staff_action_at=timezone.now(),
		)

		consultation.medical_record.follow_up_plan = self._append_note(
			consultation.medical_record.follow_up_plan,
			(
				f"Referral planned on {timezone.localtime(normalized_slot).strftime('%Y-%m-%d %H:%M')} "
				f"to Dr. {target_doctor.user.email} ({target_doctor.get_department_display()})."
			),
		)
		consultation.medical_record.save(update_fields=['follow_up_plan', 'updated_at'])

		Notification.objects.create(
			recipient=consultation.medical_record.patient.user,
			notification_type=Notification.Type.FOLLOW_UP,
			title='Referral appointment created',
			message=(
				f"A referral appointment was scheduled on "
				f"{timezone.localtime(normalized_slot).strftime('%Y-%m-%d %H:%M')} with Dr. {target_doctor.user.email}."
			),
		)

		if target_doctor.user_id != consultation.doctor.user_id:
			Notification.objects.create(
				recipient=target_doctor.user,
				notification_type=Notification.Type.FOLLOW_UP,
				title='New referred patient appointment',
				message=(
					f"A patient referral was scheduled on "
					f"{timezone.localtime(normalized_slot).strftime('%Y-%m-%d %H:%M')} "
					f"from Dr. {consultation.doctor.user.email}."
				),
			)

		return Response(
			{
				'appointment': AppointmentSerializer(appointment, context={'request': request}).data,
				'target_doctor_email': target_doctor.user.email,
				'target_department': target_doctor.department,
			},
			status=status.HTTP_201_CREATED,
		)

	def _update_record_sections_from_payload(self, medical_record, appointment, diagnosis, anamnesis, treatment_plan, payload):
		updates = {}

		consultation_motive = str(payload.get('consultation_motive', '') or '').strip() or appointment.reason
		if consultation_motive:
			updates['consultation_motive'] = consultation_motive

		if anamnesis:
			updates['current_illness_history'] = anamnesis

		if diagnosis:
			updates['diagnostic_summary'] = diagnosis

		if treatment_plan:
			updates['treatment_management'] = treatment_plan

		medical_background = str(payload.get('medical_background', '') or '').strip()
		if medical_background:
			updates['medical_background'] = medical_background

		for field in [
			'administrative_notes',
			'clinical_examination',
			'complementary_exams',
			'follow_up_plan',
			'annex_notes',
			'social_security_number',
			'chronic_conditions',
			'surgeries_history',
			'family_history',
			'immunizations',
		]:
			value = str(payload.get(field, '') or '').strip()
			if value:
				updates[field] = value

		if updates:
			for key, value in updates.items():
				setattr(medical_record, key, value)
			medical_record.save(update_fields=[*updates.keys(), 'updated_at'])

	def _extract_chatbot_diagnosis_for_appointment(self, appointment):
		window_start = appointment.created_at - timedelta(hours=24)

		candidate_messages = list(
			ChatbotMessage.objects.filter(
				session__patient=appointment.patient,
				sender=ChatbotMessage.Sender.BOT,
				created_at__gte=window_start,
				created_at__lte=appointment.created_at,
			)
			.order_by('-created_at')[:20]
		)

		for message in candidate_messages:
			metadata = message.metadata or {}
			recommendation = metadata.get('recommended_appointment') or {}
			if not recommendation.get('should_schedule'):
				continue

			probable = metadata.get('probable_diseases') or []
			urgency = metadata.get('urgency_level')
			department = metadata.get('department')

			parts = []
			if probable:
				top_probable = []
				for item in probable[:3]:
					disease = str(item.get('disease', '')).strip()
					score = item.get('score')
					if not disease:
						continue
					if score not in [None, '']:
						top_probable.append(f"{disease} ({score}%)")
					else:
						top_probable.append(disease)
				if top_probable:
					parts.append(f"Chatbot triage probable diagnosis: {', '.join(top_probable)}.")

			if urgency:
				parts.append(f"Urgency from chatbot: {urgency}.")
			if department:
				parts.append(f"Suggested department: {department}.")

			summary = str(metadata.get('summary', '') or '').strip()
			if summary:
				parts.append(summary)

			if parts:
				return ' '.join(parts)

		return ''

	@staticmethod
	def _append_note(existing_notes, new_note):
		current = (existing_notes or '').strip()
		if not current:
			return new_note
		return f"{current}\n{new_note}"


class MedicalDocumentRequestViewSet(viewsets.ModelViewSet):
	serializer_class = MedicalDocumentRequestSerializer
	queryset = MedicalDocumentRequest.objects.select_related(
		'medical_record__patient__user',
		'doctor__user',
	).prefetch_related('documents').all()
	filterset_fields = ['medical_record', 'doctor', 'request_type', 'status']
	search_fields = ['title', 'description', 'medical_record__patient__user__email']
	ordering_fields = ['created_at', 'updated_at', 'due_date']

	def get_permissions(self):
		return [permissions.IsAuthenticated()]

	def get_queryset(self):
		user = self.request.user
		qs = self.queryset
		if user.role == 'patient':
			return qs.filter(medical_record__patient__user=user)
		if user.role == 'doctor':
			return qs.filter(
				Q(doctor__user=user) | Q(medical_record__consultations__doctor__user=user)
			).distinct()
		return qs

	def perform_create(self, serializer):
		user = self.request.user
		medical_record = serializer.validated_data.get('medical_record')
		if not medical_record:
			raise ValidationError({'medical_record': 'This field is required.'})

		if user.role == 'doctor':
			doctor_profile = self._get_doctor_profile(user)
			self._ensure_doctor_can_manage_record(doctor_profile, medical_record)
			instance = serializer.save(doctor=doctor_profile)
		elif user.role == 'admin':
			doctor_profile = serializer.validated_data.get('doctor')
			if not doctor_profile:
				raise ValidationError({'doctor': 'This field is required for admin-created requests.'})
			instance = serializer.save(doctor=doctor_profile)
		else:
			raise PermissionDenied('Only doctors and admins can create document requests.')

		Notification.objects.create(
			recipient=medical_record.patient.user,
			notification_type=Notification.Type.FOLLOW_UP,
			title='New medical document request',
			message=f"Dr. {instance.doctor.user.email} requested additional documents: {instance.title}.",
		)

	def perform_update(self, serializer):
		user = self.request.user
		instance = serializer.instance
		if user.role == 'patient':
			raise PermissionDenied('Patients cannot modify document requests.')
		if user.role == 'doctor' and instance.doctor.user_id != user.id:
			raise PermissionDenied('Doctors can only update their own document requests.')

		updated = serializer.save()
		if updated.status in [MedicalDocumentRequest.Status.REVIEWED, MedicalDocumentRequest.Status.CANCELLED]:
			if not updated.closed_at:
				updated.closed_at = timezone.now()
				updated.save(update_fields=['closed_at', 'updated_at'])
		else:
			if updated.closed_at:
				updated.closed_at = None
				updated.save(update_fields=['closed_at', 'updated_at'])

	def perform_destroy(self, instance):
		user = self.request.user
		if user.role == 'patient':
			raise PermissionDenied('Patients cannot delete document requests.')
		if user.role == 'doctor' and instance.doctor.user_id != user.id:
			raise PermissionDenied('Doctors can only delete their own document requests.')
		instance.delete()

	@staticmethod
	def _get_doctor_profile(user):
		doctor_profile = DoctorProfile.objects.filter(user=user).first()
		if not doctor_profile:
			raise ValidationError({'doctor': 'Doctor profile is missing for this account.'})
		return doctor_profile

	@staticmethod
	def _ensure_doctor_can_manage_record(doctor_profile, record):
		has_consultation = Consultation.objects.filter(medical_record=record, doctor=doctor_profile).exists()
		if not has_consultation:
			raise PermissionDenied('You can only request documents for records linked to your consultations.')


class MedicalDocumentViewSet(viewsets.ModelViewSet):
	serializer_class = MedicalDocumentSerializer
	parser_classes = [MultiPartParser, FormParser, JSONParser]
	queryset = MedicalDocument.objects.select_related(
		'medical_record__patient__user',
		'request__doctor__user',
		'uploaded_by_patient__user',
		'uploaded_by_doctor__user',
		'reviewed_by__user',
	).all()
	filterset_fields = ['medical_record', 'request', 'document_type', 'review_status']
	search_fields = ['title', 'notes', 'medical_record__patient__user__email']
	ordering_fields = ['uploaded_at', 'reviewed_at']

	def get_permissions(self):
		return [permissions.IsAuthenticated()]

	def get_queryset(self):
		user = self.request.user
		qs = self.queryset
		if user.role == 'patient':
			return qs.filter(medical_record__patient__user=user)
		if user.role == 'doctor':
			return qs.filter(
				Q(medical_record__consultations__doctor__user=user)
				| Q(request__doctor__user=user)
				| Q(uploaded_by_doctor__user=user)
			).distinct()
		return qs

	def perform_create(self, serializer):
		user = self.request.user
		medical_record = serializer.validated_data.get('medical_record')
		request_obj = serializer.validated_data.get('request')

		if request_obj and request_obj.medical_record_id != medical_record.id:
			raise ValidationError({'request': 'Request must belong to the same medical record.'})

		if user.role == 'patient':
			patient_profile = PatientProfile.objects.filter(user=user).first()
			if not patient_profile:
				raise ValidationError({'patient': 'Patient profile is missing for this account.'})
			if medical_record.patient_id != patient_profile.id:
				raise PermissionDenied('You can only upload documents to your own medical record.')

			document = serializer.save(uploaded_by_patient=patient_profile, review_status=MedicalDocument.ReviewStatus.UPLOADED)

			target_doctor = None
			if request_obj:
				target_doctor = request_obj.doctor
				if request_obj.status in [MedicalDocumentRequest.Status.PENDING, MedicalDocumentRequest.Status.UPLOADED]:
					request_obj.status = MedicalDocumentRequest.Status.UPLOADED
					request_obj.closed_at = None
					request_obj.save(update_fields=['status', 'closed_at', 'updated_at'])

			if request_obj and target_doctor:
				Notification.objects.create(
					recipient=target_doctor.user,
					notification_type=Notification.Type.FOLLOW_UP,
					title='New patient document uploaded',
					message=(
						f"Patient {medical_record.patient.user.email} uploaded '{document.title}' "
						f"for request #{request_obj.id}."
					),
				)
			return

		if user.role == 'doctor':
			doctor_profile = DoctorProfile.objects.filter(user=user).first()
			if not doctor_profile:
				raise ValidationError({'doctor': 'Doctor profile is missing for this account.'})
			self._ensure_doctor_can_manage_record(doctor_profile, medical_record)
			serializer.save(uploaded_by_doctor=doctor_profile)
			return

		if user.role == 'admin':
			serializer.save()
			return

		raise PermissionDenied('You do not have permission to upload documents.')

	def perform_update(self, serializer):
		user = self.request.user
		instance = serializer.instance

		if user.role == 'patient':
			raise PermissionDenied('Patients cannot update uploaded document review fields.')

		doctor_profile = None
		if user.role == 'doctor':
			doctor_profile = DoctorProfile.objects.filter(user=user).first()
			if not doctor_profile:
				raise ValidationError({'doctor': 'Doctor profile is missing for this account.'})
			self._ensure_doctor_can_manage_record(doctor_profile, instance.medical_record)

		updated = serializer.save()
		if updated.review_status in [MedicalDocument.ReviewStatus.REVIEWED, MedicalDocument.ReviewStatus.REJECTED]:
			update_fields = ['reviewed_at']
			updated.reviewed_at = timezone.now()
			if doctor_profile:
				updated.reviewed_by = doctor_profile
				update_fields.append('reviewed_by')
			updated.save(update_fields=update_fields)

			if updated.request:
				if updated.review_status == MedicalDocument.ReviewStatus.REVIEWED:
					updated.request.status = MedicalDocumentRequest.Status.REVIEWED
					updated.request.closed_at = timezone.now()
				else:
					updated.request.status = MedicalDocumentRequest.Status.PENDING
					updated.request.closed_at = None
				updated.request.review_note = updated.review_note or updated.request.review_note
				updated.request.save(update_fields=['status', 'closed_at', 'review_note', 'updated_at'])

			Notification.objects.create(
				recipient=updated.medical_record.patient.user,
				notification_type=Notification.Type.FOLLOW_UP,
				title='Document review updated',
				message=(
					f"Document '{updated.title}' was marked as {updated.review_status}. "
					f"{updated.review_note or ''}".strip()
				),
			)

	def perform_destroy(self, instance):
		user = self.request.user
		if user.role == 'patient':
			raise PermissionDenied('Patients cannot delete uploaded documents.')
		if user.role == 'doctor':
			doctor_profile = DoctorProfile.objects.filter(user=user).first()
			if not doctor_profile:
				raise ValidationError({'doctor': 'Doctor profile is missing for this account.'})
			self._ensure_doctor_can_manage_record(doctor_profile, instance.medical_record)
		instance.delete()

	@staticmethod
	def _ensure_doctor_can_manage_record(doctor_profile, record):
		has_consultation = Consultation.objects.filter(medical_record=record, doctor=doctor_profile).exists()
		if not has_consultation:
			raise PermissionDenied('You can only manage documents for records linked to your consultations.')

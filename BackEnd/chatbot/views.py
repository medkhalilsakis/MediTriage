from django.db import transaction
from django.db.models import Q
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone

from appointments.models import Appointment
from appointments.scheduling import assign_doctor_and_slot_for_patient
from .ai_service import analyze_symptoms, build_health_chat_response
from doctors.models import DoctorProfile
from .models import ChatbotMessage, ChatbotSession
from .serializers import ChatbotMessageSerializer, ChatbotSendMessageSerializer, ChatbotSessionSerializer


APPOINTMENT_POSITIVE_ANSWERS = {
	'yes',
	'oui',
	'yeah',
	'yep',
	'ok',
	'okay',
	'daccord',
	"d'accord",
	'book',
	'book it',
	'accept',
	'i accept',
	'go ahead',
}

APPOINTMENT_NEGATIVE_ANSWERS = {
	'no',
	'non',
	'nope',
	'not now',
	'pas maintenant',
	'later',
	'cancel',
	'decline',
}

DEPARTMENT_TO_APPOINTMENT = {
	'cardiology': Appointment.Department.CARDIOLOGY,
	'pulmonology': Appointment.Department.RESPIRATORY,
	'respiratory': Appointment.Department.RESPIRATORY,
	'neurology': Appointment.Department.NEUROLOGY,
	'gastroenterology': Appointment.Department.GASTROENTEROLOGY,
	'dermatology': Appointment.Department.DERMATOLOGY,
	'endocrinology': Appointment.Department.ENDOCRINOLOGY,
	'general medicine': Appointment.Department.GENERAL_MEDICINE,
}


class PublicChatbotMessageView(APIView):
	permission_classes = [permissions.AllowAny]
	authentication_classes = []

	def post(self, request):
		serializer = ChatbotSendMessageSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)

		content = serializer.validated_data['content']
		wants_appointment = serializer.validated_data.get('wants_appointment', False)

		assistant_payload = build_health_chat_response(
			content,
			wants_appointment=wants_appointment,
			require_auth_for_booking=True,
		)

		analysis = assistant_payload.get('analysis')
		bot_metadata = {
			'response_type': assistant_payload.get('response_type'),
			'booking_auth_required': assistant_payload.get('booking_auth_required', False),
		}
		if analysis:
			bot_metadata['analysis'] = analysis

		return Response(
			{
				'patient_message': {
					'sender': ChatbotMessage.Sender.PATIENT,
					'content': content,
				},
				'bot_message': {
					'sender': ChatbotMessage.Sender.BOT,
					'content': assistant_payload.get('reply', ''),
					'metadata': bot_metadata,
				},
				'analysis': analysis,
				'response_type': assistant_payload.get('response_type'),
				'booking_auth_required': assistant_payload.get('booking_auth_required', False),
			},
			status=status.HTTP_200_OK,
		)


class ChatbotSessionViewSet(viewsets.ModelViewSet):
	serializer_class = ChatbotSessionSerializer
	queryset = ChatbotSession.objects.select_related(
		'patient__user',
		'booked_appointment__doctor__user',
	).prefetch_related('messages').all()
	filterset_fields = ['patient', 'is_closed']
	search_fields = ['title', 'patient__user__email']
	ordering_fields = ['created_at', 'updated_at']

	def get_permissions(self):
		return [permissions.IsAuthenticated()]

	def get_queryset(self):
		user = self.request.user
		qs = self.queryset
		if user.role == 'patient':
			return qs.filter(patient__user=user)
		if user.role == 'doctor':
			return qs.filter(patient__appointments__doctor__user=user).distinct()
		return qs

	def perform_create(self, serializer):
		user = self.request.user
		if user.role == 'patient':
			if not hasattr(user, 'patient_profile'):
				raise ValidationError({'patient': 'Patient profile is missing for this account.'})
			serializer.save(
				patient=user.patient_profile,
				awaiting_appointment_confirmation=False,
				latest_analysis={},
				is_closed=False,
			)
			return

		if not serializer.validated_data.get('patient'):
			raise ValidationError({'patient': 'This field is required for this role.'})
		serializer.save(
			awaiting_appointment_confirmation=False,
			latest_analysis={},
			is_closed=False,
		)

	def perform_destroy(self, instance):
		user = self.request.user
		if user.role == 'patient' and instance.patient.user_id != user.id:
			raise PermissionDenied('You can only delete your own chatbot conversations.')
		if user.role not in ['patient', 'admin']:
			raise PermissionDenied('Only patient or admin can delete chatbot conversations.')
		super().perform_destroy(instance)

	def _list_candidate_doctors(self, specialization_keywords):
		doctors_qs = DoctorProfile.objects.select_related('user').all()

		if specialization_keywords:
			lookup = Q()
			for keyword in specialization_keywords:
				lookup |= Q(specialization__icontains=keyword)
			matched = doctors_qs.filter(lookup)
			if matched.exists():
				doctors_qs = matched

		return [
			{
				'id': doctor.id,
				'email': doctor.user.email,
				'specialization': doctor.specialization,
				'years_of_experience': doctor.years_of_experience,
			}
			for doctor in doctors_qs.order_by('-years_of_experience')[:5]
		]

	@action(detail=True, methods=['post'], url_path='message')
	def message(self, request, pk=None):
		session = self.get_object()
		if request.user.role == 'patient' and session.patient.user_id != request.user.id:
			raise PermissionDenied('You can only message your own chatbot conversation.')

		if session.is_closed:
			raise ValidationError({'detail': 'This conversation is closed. Start a new conversation.'})

		serializer = ChatbotSendMessageSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		patient_content = serializer.validated_data['content']

		patient_message = ChatbotMessage.objects.create(
			session=session,
			sender=ChatbotMessage.Sender.PATIENT,
			content=patient_content,
		)

		decision = self._parse_appointment_decision(patient_content)
		if session.awaiting_appointment_confirmation:
			if decision is True:
				booking_payload = self._book_appointment_from_session(session)
				if booking_payload['created']:
					notice = booking_payload.get('notice')
					notice_line = f"{notice} " if notice else ''
					bot_reply = (
						f"Appointment booked successfully. ID: {booking_payload['appointment_id']}, "
						f"date: {booking_payload['scheduled_at']}, doctor: {booking_payload['doctor_email']}. "
						f"{notice_line}"
						"My diagnostic role for this conversation is complete. Please start a new conversation if needed."
					)
					bot_message = ChatbotMessage.objects.create(
						session=session,
						sender=ChatbotMessage.Sender.BOT,
						content=bot_reply,
						metadata={
							'appointment_booking': booking_payload,
							'conversation_closed': True,
						},
					)
					return Response(
						{
							'patient_message': ChatbotMessageSerializer(patient_message).data,
							'bot_message': ChatbotMessageSerializer(bot_message).data,
							'analysis': session.latest_analysis,
							'appointment_booking': booking_payload,
							'session': ChatbotSessionSerializer(session).data,
						},
						status=status.HTTP_201_CREATED,
					)

				bot_message = ChatbotMessage.objects.create(
					session=session,
					sender=ChatbotMessage.Sender.BOT,
					content=booking_payload['message'],
					metadata={'appointment_booking': booking_payload},
				)
				return Response(
					{
						'patient_message': ChatbotMessageSerializer(patient_message).data,
						'bot_message': ChatbotMessageSerializer(bot_message).data,
						'analysis': session.latest_analysis,
						'appointment_booking': booking_payload,
						'session': ChatbotSessionSerializer(session).data,
					},
					status=status.HTTP_201_CREATED,
				)

			if decision is False:
				session.awaiting_appointment_confirmation = False
				session.save(update_fields=['awaiting_appointment_confirmation', 'updated_at'])
				bot_message = ChatbotMessage.objects.create(
					session=session,
					sender=ChatbotMessage.Sender.BOT,
					content='Understood. No appointment has been booked. You can continue describing your symptoms.',
					metadata={'appointment_booking': {'created': False, 'declined': True}},
				)
				return Response(
					{
						'patient_message': ChatbotMessageSerializer(patient_message).data,
						'bot_message': ChatbotMessageSerializer(bot_message).data,
						'analysis': session.latest_analysis,
						'session': ChatbotSessionSerializer(session).data,
					},
					status=status.HTTP_201_CREATED,
				)

			# If answer is neither yes nor no, continue normal chatbot flow.
			session.awaiting_appointment_confirmation = False
			session.save(update_fields=['awaiting_appointment_confirmation', 'updated_at'])

		assistant_payload = build_health_chat_response(
			patient_content,
			wants_appointment=True,
			require_auth_for_booking=False,
		)

		if assistant_payload.get('response_type') != 'triage':
			analysis = assistant_payload.get('analysis') or {}
			session.awaiting_appointment_confirmation = False
			session.latest_analysis = analysis
			session.save(update_fields=['awaiting_appointment_confirmation', 'latest_analysis', 'updated_at'])

			bot_metadata = {
				'response_type': assistant_payload.get('response_type'),
				'booking_auth_required': assistant_payload.get('booking_auth_required', False),
			}
			if analysis:
				bot_metadata['analysis'] = analysis

			bot_message = ChatbotMessage.objects.create(
				session=session,
				sender=ChatbotMessage.Sender.BOT,
				content=assistant_payload.get('reply', ''),
				metadata=bot_metadata,
			)

			return Response(
				{
					'patient_message': ChatbotMessageSerializer(patient_message).data,
					'bot_message': ChatbotMessageSerializer(bot_message).data,
					'analysis': analysis,
					'session': ChatbotSessionSerializer(session).data,
				},
				status=status.HTTP_201_CREATED,
			)

		analysis = assistant_payload.get('analysis') or analyze_symptoms(
			patient_content,
			wants_appointment=True,
		)
		bot_reply = (assistant_payload.get('reply') or '').strip()

		recommendation = analysis.get('recommended_appointment', {})
		if recommendation.get('should_schedule'):
			recommended_keywords = analysis.get('department_matching_keywords', [])
			recommendation['candidate_doctors'] = self._list_candidate_doctors(recommended_keywords)

		if analysis.get('probable_diseases'):
			session.awaiting_appointment_confirmation = True
			session.latest_analysis = analysis
			session.save(update_fields=['awaiting_appointment_confirmation', 'latest_analysis', 'updated_at'])
			confirmation_prompt = (
				'\n\nBooking confirmation:\n'
				'- I can book this appointment now.\n'
				'- Reply with yes to confirm or no to continue without booking.'
			)
			bot_reply = f'{bot_reply}{confirmation_prompt}' if bot_reply else confirmation_prompt.strip()
		else:
			session.awaiting_appointment_confirmation = False
			session.latest_analysis = analysis
			session.save(update_fields=['awaiting_appointment_confirmation', 'latest_analysis', 'updated_at'])
			if not bot_reply:
				bot_reply = 'I need more specific symptoms to propose a diagnosis and appointment booking.'

		bot_message = ChatbotMessage.objects.create(
			session=session,
			sender=ChatbotMessage.Sender.BOT,
			content=bot_reply,
			metadata=analysis,
		)

		return Response(
			{
				'patient_message': ChatbotMessageSerializer(patient_message).data,
				'bot_message': ChatbotMessageSerializer(bot_message).data,
				'analysis': analysis,
				'session': ChatbotSessionSerializer(session).data,
			},
			status=status.HTTP_201_CREATED,
		)

	def _parse_appointment_decision(self, text):
		normalized = ' '.join((text or '').strip().lower().split())
		if not normalized:
			return None
		if normalized in APPOINTMENT_POSITIVE_ANSWERS:
			return True
		if normalized in APPOINTMENT_NEGATIVE_ANSWERS:
			return False
		return None

	def _book_appointment_from_session(self, session):
		if session.booked_appointment_id:
			appointment = session.booked_appointment
			return {
				'created': False,
				'already_exists': True,
				'appointment_id': appointment.id,
				'scheduled_at': appointment.scheduled_at.isoformat(),
				'doctor_email': appointment.doctor.user.email,
				'message': 'An appointment was already booked for this conversation.',
			}

		analysis = session.latest_analysis or {}
		department = self._map_department_to_appointment(analysis.get('department'))
		urgency = str(analysis.get('urgency_level') or 'medium').lower()
		if urgency not in Appointment.UrgencyLevel.values:
			urgency = Appointment.UrgencyLevel.MEDIUM

		reason = self._build_appointment_reason_from_analysis(analysis)

		with transaction.atomic():
			doctor, scheduled_at, effective_department, conflicting_appointment = assign_doctor_and_slot_for_patient(
				requested_department=department,
				patient=session.patient,
				now=None,
			)

			if not doctor or not scheduled_at:
				session.awaiting_appointment_confirmation = False
				session.save(update_fields=['awaiting_appointment_confirmation', 'updated_at'])
				return {
					'created': False,
					'message': 'No doctor is currently available for automated booking. Please try again later.',
				}

			appointment = Appointment.objects.create(
				patient=session.patient,
				doctor=doctor,
				scheduled_at=scheduled_at,
				status=Appointment.Status.CONFIRMED,
				urgency_level=urgency,
				department=effective_department,
				reason=reason,
				notes=(
					f"Automatically booked from chatbot conversation #{session.id}. "
					f"Summary: {analysis.get('summary', '')}"
				).strip(),
			)

			session.booked_appointment = appointment
			session.awaiting_appointment_confirmation = False
			session.is_closed = True
			session.save(update_fields=['booked_appointment', 'awaiting_appointment_confirmation', 'is_closed', 'updated_at'])

		notice = None
		if conflicting_appointment and conflicting_appointment.scheduled_at:
			existing_label = timezone.localtime(conflicting_appointment.scheduled_at).strftime('%Y-%m-%d %H:%M')
			new_label = timezone.localtime(appointment.scheduled_at).strftime('%Y-%m-%d %H:%M')
			notice = (
				'Multiple appointments on the same day are not allowed. '
				f'Your existing appointment is on {existing_label}, so this booking was moved to {new_label}.'
			)

		return {
			'created': True,
			'appointment_id': appointment.id,
			'scheduled_at': appointment.scheduled_at.isoformat(),
			'doctor_email': appointment.doctor.user.email,
			'department': appointment.department,
			'urgency_level': appointment.urgency_level,
			'same_day_limit_applied': bool(conflicting_appointment),
			'notice': notice,
		}

	def _map_department_to_appointment(self, department_name):
		normalized = str(department_name or '').strip().lower()
		return DEPARTMENT_TO_APPOINTMENT.get(normalized, Appointment.Department.GENERAL_MEDICINE)

	def _build_appointment_reason_from_analysis(self, analysis):
		probable_diseases = analysis.get('probable_diseases') or []
		detected_symptoms = analysis.get('detected_symptoms') or []

		parts = ['Chatbot triage booking']
		if probable_diseases:
			top = probable_diseases[0].get('disease')
			if top:
				parts.append(f"suspected condition: {top}")

		if detected_symptoms:
			parts.append(f"symptoms: {', '.join(detected_symptoms[:5])}")

		return ' | '.join(parts)

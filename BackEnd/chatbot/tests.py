from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from appointments.models import Appointment
from authentication.models import CustomUser
from doctors.models import DoctorProfile
from patients.models import PatientProfile

from .models import ChatbotSession


@override_settings(TIME_ZONE='UTC', USE_TZ=True)
class ChatbotConversationFlowTests(APITestCase):
	def setUp(self):
		self.patient_user = self._create_user('patient-chat@meditriage.test', CustomUser.Role.PATIENT)
		self.patient_profile = PatientProfile.objects.create(user=self.patient_user)

		self.doctor_user = self._create_user('doctor-chat@meditriage.test', CustomUser.Role.DOCTOR)
		self.doctor_profile = DoctorProfile.objects.create(
			user=self.doctor_user,
			specialization='General specialist',
			department=DoctorProfile.Department.GENERAL_MEDICINE,
			license_number='DOC-CHAT-001',
		)

	def test_patient_can_manage_multiple_conversations_and_delete(self):
		self.client.force_authenticate(user=self.patient_user)

		first = self.client.post('/api/chatbot/sessions/', {'title': 'Conversation A'}, format='json')
		second = self.client.post('/api/chatbot/sessions/', {'title': 'Conversation B'}, format='json')

		self.assertEqual(first.status_code, status.HTTP_201_CREATED)
		self.assertEqual(second.status_code, status.HTTP_201_CREATED)

		list_response = self.client.get('/api/chatbot/sessions/')
		self.assertEqual(list_response.status_code, status.HTTP_200_OK)
		items = list_response.data.get('results', list_response.data)
		self.assertGreaterEqual(len(items), 2)

		delete_response = self.client.delete(f"/api/chatbot/sessions/{first.data['id']}/")
		self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)

		list_response = self.client.get('/api/chatbot/sessions/')
		items = list_response.data.get('results', list_response.data)
		ids = {item['id'] for item in items}
		self.assertNotIn(first.data['id'], ids)
		self.assertIn(second.data['id'], ids)

	def test_chatbot_acceptance_books_one_appointment_and_closes_conversation(self):
		self.client.force_authenticate(user=self.patient_user)
		session_response = self.client.post('/api/chatbot/sessions/', {'title': 'Booking flow'}, format='json')
		self.assertEqual(session_response.status_code, status.HTTP_201_CREATED)
		session_id = session_response.data['id']

		diagnosis_response = self.client.post(
			f'/api/chatbot/sessions/{session_id}/message/',
			{'content': 'I have fever, cough and chest pain for two days.'},
			format='json',
		)
		self.assertEqual(diagnosis_response.status_code, status.HTTP_201_CREATED)
		self.assertTrue(diagnosis_response.data['session']['awaiting_appointment_confirmation'])

		accept_response = self.client.post(
			f'/api/chatbot/sessions/{session_id}/message/',
			{'content': 'yes'},
			format='json',
		)
		self.assertEqual(accept_response.status_code, status.HTTP_201_CREATED)
		self.assertTrue(accept_response.data['appointment_booking']['created'])

		session = ChatbotSession.objects.get(pk=session_id)
		self.assertTrue(session.is_closed)
		self.assertIsNotNone(session.booked_appointment_id)

		appointments = Appointment.objects.filter(patient=self.patient_profile)
		self.assertEqual(appointments.count(), 1)

		closed_response = self.client.post(
			f'/api/chatbot/sessions/{session_id}/message/',
			{'content': 'new symptoms after booking'},
			format='json',
		)
		self.assertEqual(closed_response.status_code, status.HTTP_400_BAD_REQUEST)

	def test_chatbot_decline_continues_conversation_without_booking(self):
		self.client.force_authenticate(user=self.patient_user)
		session_response = self.client.post('/api/chatbot/sessions/', {'title': 'No booking flow'}, format='json')
		self.assertEqual(session_response.status_code, status.HTTP_201_CREATED)
		session_id = session_response.data['id']

		first_response = self.client.post(
			f'/api/chatbot/sessions/{session_id}/message/',
			{'content': 'I feel dizziness and nausea.'},
			format='json',
		)
		self.assertEqual(first_response.status_code, status.HTTP_201_CREATED)
		self.assertTrue(first_response.data['session']['awaiting_appointment_confirmation'])

		decline_response = self.client.post(
			f'/api/chatbot/sessions/{session_id}/message/',
			{'content': 'no'},
			format='json',
		)
		self.assertEqual(decline_response.status_code, status.HTTP_201_CREATED)

		session = ChatbotSession.objects.get(pk=session_id)
		self.assertFalse(session.is_closed)
		self.assertFalse(session.awaiting_appointment_confirmation)
		self.assertIsNone(session.booked_appointment_id)

		follow_up_response = self.client.post(
			f'/api/chatbot/sessions/{session_id}/message/',
			{'content': 'Now I also have a mild fever.'},
			format='json',
		)
		self.assertEqual(follow_up_response.status_code, status.HTTP_201_CREATED)

	@staticmethod
	def _create_user(email, role):
		return CustomUser.objects.create_user(
			email=email,
			username=email.split('@')[0],
			password='StrongPass123!',
			role=role,
			is_active=True,
		)


class PublicChatbotEndpointTests(APITestCase):
	def test_public_chatbot_allows_anonymous_health_triage(self):
		response = self.client.post(
			'/api/chatbot/public/message/',
			{'content': 'I have fever, cough, and headache for two days.'},
			format='json',
		)

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data['response_type'], 'triage')
		self.assertIn('bot_message', response.data)
		self.assertIsInstance(response.data.get('analysis'), dict)

	def test_public_chatbot_rejects_out_of_scope_requests(self):
		response = self.client.post(
			'/api/chatbot/public/message/',
			{'content': 'Write me a JavaScript sorting algorithm.'},
			format='json',
		)

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data['response_type'], 'out_of_scope')
		self.assertIn('healthcare triage chatbot', response.data['bot_message']['content'].lower())

	def test_public_chatbot_booking_requires_authentication(self):
		response = self.client.post(
			'/api/chatbot/public/message/',
			{'content': 'I have chest pain and fever, please book an appointment now.'},
			format='json',
		)

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertTrue(response.data['booking_auth_required'])
		self.assertIn('log in or sign up', response.data['bot_message']['content'].lower())

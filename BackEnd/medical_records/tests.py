from datetime import datetime, timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from appointments.models import Appointment
from authentication.models import CustomUser
from chatbot.models import ChatbotMessage, ChatbotSession
from doctors.models import DoctorProfile
from follow_up.models import FollowUp
from patients.models import PatientProfile

from .models import Consultation, MedicalDocument, MedicalDocumentRequest, MedicalRecord


@override_settings(TIME_ZONE='UTC', USE_TZ=True)
class ConsultationFromAppointmentTests(APITestCase):
	def setUp(self):
		self.patient_user = self._create_user('patient-records@meditriage.test', CustomUser.Role.PATIENT)
		self.patient_profile = PatientProfile.objects.create(user=self.patient_user)

		self.doctor_user = self._create_user('doctor-records@meditriage.test', CustomUser.Role.DOCTOR)
		self.doctor_profile = DoctorProfile.objects.create(
			user=self.doctor_user,
			specialization='General specialist',
			department=DoctorProfile.Department.GENERAL_MEDICINE,
			license_number='DOC-RECORD-001',
		)

	def test_create_record_from_appointment_with_chatbot_diagnosis(self):
		session = ChatbotSession.objects.create(patient=self.patient_profile, title='Triage')
		ChatbotMessage.objects.create(
			session=session,
			sender=ChatbotMessage.Sender.BOT,
			content='Preliminary triage',
			metadata={
				'recommended_appointment': {'should_schedule': True},
				'probable_diseases': [
					{'disease': 'Flu', 'score': 82.3},
					{'disease': 'Common Cold', 'score': 60.0},
				],
				'urgency_level': 'medium',
				'department': 'General Medicine',
				'summary': 'AI triage recommendation.',
			},
		)

		appointment = Appointment.objects.create(
			patient=self.patient_profile,
			doctor=self.doctor_profile,
			scheduled_at=self._dt(days=1, hour=10),
			status=Appointment.Status.CONFIRMED,
			reason='Fever and cough',
			department=self.doctor_profile.department,
		)

		self.client.force_authenticate(user=self.doctor_user)
		response = self.client.post(
			'/api/medical-records/consultations/create-from-appointment/',
			{
				'appointment_id': appointment.id,
				'diagnosis': 'Doctor final diagnosis',
				'anamnesis': 'Patient reports symptoms for 3 days.',
			},
			format='json',
		)

		self.assertEqual(response.status_code, status.HTTP_201_CREATED)
		self.assertTrue(response.data['created'])
		self.assertIn('medical_record', response.data)
		self.assertIn('consultation', response.data)
		self.assertTrue(response.data['medical_record']['id'])

		consultation = Consultation.objects.get(pk=response.data['consultation']['id'])
		self.assertEqual(consultation.diagnosis, 'Doctor final diagnosis')
		self.assertIn('Flu', consultation.chatbot_diagnosis)

		appointment.refresh_from_db()
		self.assertEqual(appointment.status, Appointment.Status.COMPLETED)

	def test_create_record_without_chatbot_referral_keeps_chatbot_diagnosis_empty(self):
		appointment = Appointment.objects.create(
			patient=self.patient_profile,
			doctor=self.doctor_profile,
			scheduled_at=self._dt(days=1, hour=11),
			status=Appointment.Status.CONFIRMED,
			reason='Routine check-up',
			department=self.doctor_profile.department,
		)

		self.client.force_authenticate(user=self.doctor_user)
		response = self.client.post(
			'/api/medical-records/consultations/create-from-appointment/',
			{
				'appointment_id': appointment.id,
				'diagnosis': 'No serious issue detected',
			},
			format='json',
		)

		self.assertEqual(response.status_code, status.HTTP_201_CREATED)
		consultation = Consultation.objects.get(pk=response.data['consultation']['id'])
		self.assertEqual(consultation.chatbot_diagnosis, '')

		medical_record = MedicalRecord.objects.get(pk=response.data['medical_record']['id'])
		self.assertEqual(medical_record.patient_id, self.patient_profile.id)

	@staticmethod
	def _create_user(email, role):
		return CustomUser.objects.create_user(
			email=email,
			username=email.split('@')[0],
			password='StrongPass123!',
			role=role,
			is_active=True,
		)

	@staticmethod
	def _dt(days, hour, minute=0):
		target = timezone.now() + timedelta(days=days)
		naive = datetime(target.year, target.month, target.day, hour, minute, 0)
		return timezone.make_aware(naive, timezone.get_current_timezone())


@override_settings(TIME_ZONE='UTC', USE_TZ=True)
class MedicalDocumentWorkflowTests(APITestCase):
	def setUp(self):
		self.patient_user = self._create_user('patient-docs@meditriage.test', CustomUser.Role.PATIENT)
		self.patient_user.first_name = 'John'
		self.patient_user.last_name = 'Doe'
		self.patient_user.phone_number = '+213550000000'
		self.patient_user.save(update_fields=['first_name', 'last_name', 'phone_number'])

		self.patient_profile = PatientProfile.objects.create(
			user=self.patient_user,
			gender='male',
			address='Test address',
			emergency_contact_name='Relative',
			emergency_contact_phone='+213660000000',
		)

		self.doctor_user = self._create_user('doctor-docs@meditriage.test', CustomUser.Role.DOCTOR)
		self.doctor_profile = DoctorProfile.objects.create(
			user=self.doctor_user,
			specialization='General specialist',
			department=DoctorProfile.Department.GENERAL_MEDICINE,
			license_number='DOC-RECORD-002',
		)
		self.referral_doctor_user = self._create_user('doctor-referral@meditriage.test', CustomUser.Role.DOCTOR)
		self.referral_doctor = DoctorProfile.objects.create(
			user=self.referral_doctor_user,
			specialization='Cardiology specialist',
			department=DoctorProfile.Department.CARDIOLOGY,
			license_number='DOC-RECORD-003',
		)

		self.medical_record = MedicalRecord.objects.create(patient=self.patient_profile)
		self.consultation = Consultation.objects.create(
			medical_record=self.medical_record,
			doctor=self.doctor_profile,
			diagnosis='Initial diagnosis',
		)

	def test_doctor_can_create_document_request(self):
		self.client.force_authenticate(user=self.doctor_user)
		response = self.client.post(
			'/api/medical-records/requests/',
			{
				'medical_record': self.medical_record.id,
				'request_type': MedicalDocumentRequest.RequestType.ANALYSIS,
				'title': 'Blood test request',
				'description': 'Please upload CBC and CRP results.',
				'requested_items': ['CBC', 'CRP'],
			},
			format='json',
		)

		self.assertEqual(response.status_code, status.HTTP_201_CREATED)
		self.assertEqual(response.data['doctor'], self.doctor_profile.id)
		self.assertEqual(response.data['status'], MedicalDocumentRequest.Status.PENDING)

	def test_patient_cannot_create_document_request(self):
		self.client.force_authenticate(user=self.patient_user)
		response = self.client.post(
			'/api/medical-records/requests/',
			{
				'medical_record': self.medical_record.id,
				'request_type': MedicalDocumentRequest.RequestType.DOCUMENT,
				'title': 'Unauthorized request',
			},
			format='json',
		)

		self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

	def test_patient_upload_updates_request_status_to_uploaded(self):
		document_request = MedicalDocumentRequest.objects.create(
			medical_record=self.medical_record,
			doctor=self.doctor_profile,
			request_type=MedicalDocumentRequest.RequestType.ANALYSIS,
			title='Upload blood test',
		)

		self.client.force_authenticate(user=self.patient_user)
		response = self.client.post(
			'/api/medical-records/documents/',
			{
				'medical_record': self.medical_record.id,
				'request': document_request.id,
				'document_type': MedicalDocument.DocumentType.ANALYSIS_REPORT,
				'title': 'CBC report',
				'notes': 'Uploaded from external lab.',
				'file': SimpleUploadedFile('cbc-report.txt', b'hemoglobin: 13.2'),
			},
			format='multipart',
		)

		self.assertEqual(response.status_code, status.HTTP_201_CREATED)
		self.assertEqual(response.data['review_status'], MedicalDocument.ReviewStatus.UPLOADED)

		document_request.refresh_from_db()
		self.assertEqual(document_request.status, MedicalDocumentRequest.Status.UPLOADED)

	def test_doctor_review_document_marks_request_reviewed(self):
		document_request = MedicalDocumentRequest.objects.create(
			medical_record=self.medical_record,
			doctor=self.doctor_profile,
			request_type=MedicalDocumentRequest.RequestType.ANALYSIS,
			title='Upload blood test',
			status=MedicalDocumentRequest.Status.UPLOADED,
		)
		document = MedicalDocument.objects.create(
			medical_record=self.medical_record,
			request=document_request,
			uploaded_by_patient=self.patient_profile,
			document_type=MedicalDocument.DocumentType.ANALYSIS_REPORT,
			title='CBC report',
			file=SimpleUploadedFile('cbc-review.txt', b'lab values'),
		)

		self.client.force_authenticate(user=self.doctor_user)
		response = self.client.patch(
			f'/api/medical-records/documents/{document.id}/',
			{
				'review_status': MedicalDocument.ReviewStatus.REVIEWED,
				'review_note': 'Results reviewed and accepted.',
			},
			format='json',
		)

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data['review_status'], MedicalDocument.ReviewStatus.REVIEWED)

		document_request.refresh_from_db()
		self.assertEqual(document_request.status, MedicalDocumentRequest.Status.REVIEWED)

	def test_doctor_can_schedule_follow_up_from_consultation(self):
		scheduled_at = self._dt(days=2, hour=10)

		self.client.force_authenticate(user=self.doctor_user)
		response = self.client.post(
			f'/api/medical-records/consultations/{self.consultation.id}/schedule-follow-up/',
			{
				'scheduled_at': scheduled_at.isoformat(),
				'notes': 'Control after treatment.',
				'reason': 'Follow-up control',
			},
			format='json',
		)

		self.assertEqual(response.status_code, status.HTTP_201_CREATED)
		self.assertIn('appointment', response.data)
		self.assertIn('follow_up', response.data)

		self.assertTrue(
			Appointment.objects.filter(
				id=response.data['appointment']['id'],
				doctor=self.doctor_profile,
				patient=self.patient_profile,
			).exists()
		)
		self.assertTrue(
			FollowUp.objects.filter(
				id=response.data['follow_up']['id'],
				doctor=self.doctor_profile,
				patient=self.patient_profile,
				consultation=self.consultation,
			).exists()
		)

	def test_doctor_can_refer_patient_to_other_department(self):
		scheduled_at = self._dt(days=3, hour=11)

		self.client.force_authenticate(user=self.doctor_user)
		response = self.client.post(
			f'/api/medical-records/consultations/{self.consultation.id}/refer/',
			{
				'target_doctor_id': self.referral_doctor.id,
				'department': self.referral_doctor.department,
				'scheduled_at': scheduled_at.isoformat(),
				'reason': 'Cardiology referral',
				'notes': 'Please evaluate chest pain history.',
			},
			format='json',
		)

		self.assertEqual(response.status_code, status.HTTP_201_CREATED)
		self.assertIn('appointment', response.data)

		appointment = Appointment.objects.get(pk=response.data['appointment']['id'])
		self.assertEqual(appointment.doctor_id, self.referral_doctor.id)
		self.assertEqual(appointment.department, self.referral_doctor.department)
		self.assertEqual(appointment.patient_id, self.patient_profile.id)

	def test_doctor_can_archive_and_reopen_medical_record(self):
		self.client.force_authenticate(user=self.doctor_user)

		archive_response = self.client.post(f'/api/medical-records/records/{self.medical_record.id}/archive/')
		self.assertEqual(archive_response.status_code, status.HTTP_200_OK)
		self.assertEqual(archive_response.data['status'], MedicalRecord.Status.ARCHIVED)

		reopen_response = self.client.post(f'/api/medical-records/records/{self.medical_record.id}/reopen/')
		self.assertEqual(reopen_response.status_code, status.HTTP_200_OK)
		self.assertEqual(reopen_response.data['status'], MedicalRecord.Status.ACTIVE)

	def test_doctor_can_save_specialty_assessment_and_longitudinal_metrics(self):
		self.client.force_authenticate(user=self.doctor_user)

		response = self.client.patch(
			f'/api/medical-records/records/{self.medical_record.id}/',
			{
				'specialty_assessments': [
					{
						'department': self.doctor_profile.department,
						'doctor_email': self.doctor_user.email,
						'checked_items': ['blood-pressure-risk', 'diabetes-screening'],
						'opinion': 'Initial GP opinion',
						'confidence_level': 'high',
					},
				],
				'longitudinal_metrics': [
					{
						'metric_type': 'blood_pressure',
						'period_start': '2026-03-01',
						'period_end': '2026-03-15',
						'recorded_at': '2026-03-10T09:00:00Z',
						'value_primary': 145,
						'value_secondary': 95,
						'unit': 'mmHg',
					},
				],
			},
			format='json',
		)

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(len(response.data['specialty_assessments']), 1)
		self.assertEqual(len(response.data['longitudinal_metrics']), 1)

		self.medical_record.refresh_from_db()
		self.assertEqual(len(self.medical_record.specialty_assessments), 1)
		self.assertEqual(len(self.medical_record.longitudinal_metrics), 1)

	@staticmethod
	def _create_user(email, role):
		return CustomUser.objects.create_user(
			email=email,
			username=email.split('@')[0],
			password='StrongPass123!',
			role=role,
			is_active=True,
		)

	@staticmethod
	def _dt(days, hour, minute=0):
		target = timezone.now() + timedelta(days=days)
		naive = datetime(target.year, target.month, target.day, hour, minute, 0)
		return timezone.make_aware(naive, timezone.get_current_timezone())

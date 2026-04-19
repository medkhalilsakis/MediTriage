from datetime import timedelta

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from django.core.files.uploadedfile import SimpleUploadedFile

from appointments.models import Appointment
from patients.models import PatientProfile

from doctors.models import DoctorProfile
from medical_records.models import MedicalRecord

from .models import CustomUser


class RegisterDoctorValidationTests(APITestCase):
	def setUp(self):
		existing_user = CustomUser.objects.create_user(
			email='existing-doctor@meditriage.test',
			username='existing-doctor',
			password='StrongPass123!',
			role=CustomUser.Role.DOCTOR,
			is_active=True,
		)

		DoctorProfile.objects.create(
			user=existing_user,
			specialization='General specialist',
			department=DoctorProfile.Department.GENERAL_MEDICINE,
			license_number='DOC-LICENSE-001',
		)

	def test_register_doctor_with_duplicate_license_returns_400(self):
		response = self.client.post(
			'/api/auth/register/',
			{
				'email': 'new-doctor@meditriage.test',
				'username': 'new-doctor',
				'password': 'StrongPass123!',
				'first_name': 'New',
				'last_name': 'Doctor',
				'phone_number': '+213550000001',
				'role': CustomUser.Role.DOCTOR,
				'specialization': 'General specialist',
				'department': DoctorProfile.Department.GENERAL_MEDICINE,
				'license_number': 'DOC-LICENSE-001',
			},
			format='json',
		)

		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
		self.assertIn('license_number', response.data)
		self.assertFalse(CustomUser.objects.filter(email='new-doctor@meditriage.test').exists())

	def test_register_admin_accepts_blank_doctor_fields(self):
		response = self.client.post(
			'/api/auth/register/',
			{
				'email': 'new-admin@meditriage.test',
				'username': 'new-admin',
				'password': 'StrongPass123!',
				'first_name': 'Main',
				'last_name': 'Admin',
				'phone_number': '+213550000002',
				'role': CustomUser.Role.ADMIN,
				'specialization': '',
				'department': '',
				'license_number': '',
			},
			format='json',
		)

		self.assertEqual(response.status_code, status.HTTP_201_CREATED)
		self.assertEqual(response.data.get('user', {}).get('role'), CustomUser.Role.ADMIN)

		created_user = CustomUser.objects.get(email='new-admin@meditriage.test')
		self.assertEqual(created_user.role, CustomUser.Role.ADMIN)
		self.assertFalse(DoctorProfile.objects.filter(user=created_user).exists())


class AccountMeRoleSettingsTests(APITestCase):
	def test_doctor_can_update_profile_and_image_via_me(self):
		doctor_user = CustomUser.objects.create_user(
			email='doctor-settings@meditriage.test',
			username='doctor-settings',
			password='StrongPass123!',
			role=CustomUser.Role.DOCTOR,
			is_active=True,
		)
		doctor_profile = DoctorProfile.objects.create(
			user=doctor_user,
			specialization='General specialist',
			department=DoctorProfile.Department.GENERAL_MEDICINE,
			license_number='DOC-SETTINGS-001',
		)

		self.client.force_authenticate(user=doctor_user)
		response = self.client.patch(
			'/api/auth/me/',
			{
				'first_name': 'Nora',
				'last_name': 'Haddad',
				'phone_number': '+213550111222',
				'specialization': 'Cardiology specialist',
				'department': DoctorProfile.Department.CARDIOLOGY,
				'license_number': 'DOC-SETTINGS-001-UPDATED',
				'years_of_experience': 9,
				'consultation_fee': '2500.00',
				'bio': 'Interventional cardiology',
				'profile_image': SimpleUploadedFile(
					'avatar.png',
					b'\x89PNG\r\n\x1a\n',
					content_type='image/png',
				),
			},
			format='multipart',
		)

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data['first_name'], 'Nora')
		self.assertEqual(response.data['department'], DoctorProfile.Department.CARDIOLOGY)
		self.assertIn('profile_image_url', response.data)

		doctor_profile.refresh_from_db()
		self.assertEqual(doctor_profile.specialization, 'Cardiology specialist')
		self.assertEqual(doctor_profile.license_number, 'DOC-SETTINGS-001-UPDATED')

	def test_patient_can_update_extended_patient_fields_via_me(self):
		patient_user = CustomUser.objects.create_user(
			email='patient-settings@meditriage.test',
			username='patient-settings',
			password='StrongPass123!',
			role=CustomUser.Role.PATIENT,
			is_active=True,
		)
		PatientProfile.objects.create(user=patient_user)

		self.client.force_authenticate(user=patient_user)
		response = self.client.patch(
			'/api/auth/me/',
			{
				'dob': '1995-05-15',
				'gender': 'female',
				'blood_group': 'A+',
				'allergies': 'Penicillin',
				'emergency_contact_name': 'Sister',
				'emergency_contact_phone': '+213660000001',
				'address': 'Algiers city center',
			},
			format='json',
		)

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data['gender'], 'female')
		self.assertEqual(response.data['allergies'], 'Penicillin')

		patient_user.patient_profile.refresh_from_db()
		self.assertEqual(patient_user.patient_profile.blood_group, 'A+')

	def test_admin_can_update_identity_and_image_via_me(self):
		admin_user = CustomUser.objects.create_user(
			email='admin-settings@meditriage.test',
			username='admin-settings',
			password='StrongPass123!',
			role=CustomUser.Role.ADMIN,
			is_staff=True,
			is_active=True,
		)

		self.client.force_authenticate(user=admin_user)
		response = self.client.patch(
			'/api/auth/me/',
			{
				'first_name': 'Main',
				'last_name': 'Admin',
				'profile_image': SimpleUploadedFile(
					'admin-avatar.webp',
					b'RIFF....WEBPVP8 ',
					content_type='image/webp',
				),
			},
			format='multipart',
		)

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data['first_name'], 'Main')
		self.assertNotEqual(response.data.get('profile_image_url', ''), '')


class PatientSelfDeleteAccountTests(APITestCase):
	def test_patient_can_delete_account_and_history_is_anonymized(self):
		doctor_user = CustomUser.objects.create_user(
			email='doctor-history@meditriage.test',
			username='doctor-history',
			password='StrongPass123!',
			role=CustomUser.Role.DOCTOR,
			is_active=True,
		)
		doctor_profile = DoctorProfile.objects.create(
			user=doctor_user,
			specialization='General specialist',
			department=DoctorProfile.Department.GENERAL_MEDICINE,
			license_number='DOC-HISTORY-001',
		)

		patient_user = CustomUser.objects.create_user(
			email='patient-delete-self@meditriage.test',
			username='patient-delete-self',
			password='StrongPass123!',
			role=CustomUser.Role.PATIENT,
			first_name='Test',
			last_name='Patient',
			phone_number='+213660123456',
			is_active=True,
		)
		patient_profile = PatientProfile.objects.create(
			user=patient_user,
			gender=PatientProfile.Gender.FEMALE,
			blood_group=PatientProfile.BloodGroup.A_POS,
			allergies='Penicillin',
			emergency_contact_name='Relative',
			emergency_contact_phone='+213660000000',
			address='Algiers',
		)

		medical_record = MedicalRecord.objects.create(
			patient=patient_profile,
			status=MedicalRecord.Status.ACTIVE,
			patient_full_name='Test Patient',
			patient_phone='+213660123456',
		)

		now = timezone.now()
		past_appointment = Appointment.objects.create(
			patient=patient_profile,
			doctor=doctor_profile,
			scheduled_at=now - timedelta(days=1),
			status=Appointment.Status.COMPLETED,
			reason='Past consultation',
		)
		future_appointment = Appointment.objects.create(
			patient=patient_profile,
			doctor=doctor_profile,
			scheduled_at=now + timedelta(days=2),
			status=Appointment.Status.CONFIRMED,
			reason='Future consultation',
		)

		self.client.force_authenticate(user=patient_user)
		response = self.client.delete('/api/auth/me/')

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data.get('history_owner_label'), 'deleted user')
		self.assertFalse(CustomUser.objects.filter(pk=patient_user.id).exists())

		patient_profile.refresh_from_db()
		self.assertTrue(patient_profile.is_account_deleted)
		self.assertEqual(patient_profile.get_public_identity_label(), 'deleted user')
		self.assertEqual(patient_profile.user.first_name, 'Deleted')
		self.assertEqual(patient_profile.user.last_name, 'User')
		self.assertFalse(patient_profile.user.is_active)

		self.assertTrue(Appointment.objects.filter(pk=past_appointment.id).exists())
		self.assertFalse(Appointment.objects.filter(pk=future_appointment.id).exists())

		medical_record.refresh_from_db()
		self.assertEqual(medical_record.patient_full_name, 'deleted user')
		self.assertEqual(medical_record.patient_phone, '')
		self.assertEqual(medical_record.status, MedicalRecord.Status.ARCHIVED)

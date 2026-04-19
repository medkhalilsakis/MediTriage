from datetime import timedelta

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from appointments.models import Appointment
from authentication.models import CustomUser
from doctors.models import DoctorProfile
from medical_records.models import MedicalRecord

from .models import PatientProfile


class AdminPatientAccountDeletionTests(APITestCase):
	def setUp(self):
		self.admin_user = CustomUser.objects.create_user(
			email='admin-patient-delete@meditriage.test',
			username='admin-patient-delete',
			password='StrongPass123!',
			role=CustomUser.Role.ADMIN,
			is_staff=True,
			is_active=True,
		)

		doctor_user = CustomUser.objects.create_user(
			email='doctor-patient-delete@meditriage.test',
			username='doctor-patient-delete',
			password='StrongPass123!',
			role=CustomUser.Role.DOCTOR,
			is_active=True,
		)
		self.doctor_profile = DoctorProfile.objects.create(
			user=doctor_user,
			specialization='General specialist',
			department=DoctorProfile.Department.GENERAL_MEDICINE,
			license_number='DOC-PAT-DEL-001',
		)

		self.patient_user = CustomUser.objects.create_user(
			email='patient-delete@meditriage.test',
			username='patient-delete',
			password='StrongPass123!',
			role=CustomUser.Role.PATIENT,
			is_active=True,
		)
		self.patient_profile = PatientProfile.objects.create(user=self.patient_user)

		self.medical_record = MedicalRecord.objects.create(
			patient=self.patient_profile,
			status=MedicalRecord.Status.ACTIVE,
		)

		now = timezone.now()
		self.past_appointment = Appointment.objects.create(
			patient=self.patient_profile,
			doctor=self.doctor_profile,
			scheduled_at=now - timedelta(days=2),
			status=Appointment.Status.COMPLETED,
			reason='Past consultation',
		)
		self.future_appointment = Appointment.objects.create(
			patient=self.patient_profile,
			doctor=self.doctor_profile,
			scheduled_at=now + timedelta(days=2),
			status=Appointment.Status.CONFIRMED,
			reason='Future consultation',
		)

	def test_admin_delete_account_archives_record_and_removes_future_appointments(self):
		self.client.force_authenticate(user=self.admin_user)

		response = self.client.post(
			f'/api/patients/{self.patient_profile.id}/delete-account/',
			{},
			format='json',
		)

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data['removed_future_appointments'], 1)
		self.assertTrue(response.data['medical_record_archived'])

		self.patient_user.refresh_from_db()
		self.patient_profile.refresh_from_db()
		self.medical_record.refresh_from_db()

		self.assertFalse(self.patient_user.is_active)
		self.assertTrue(self.patient_profile.is_account_deleted)
		self.assertEqual(self.patient_profile.deleted_by_id, self.admin_user.id)
		self.assertIsNotNone(self.patient_profile.account_deleted_at)
		self.assertEqual(self.medical_record.status, MedicalRecord.Status.ARCHIVED)
		self.assertEqual(self.medical_record.archived_by_id, self.admin_user.id)

		self.assertTrue(Appointment.objects.filter(pk=self.past_appointment.id).exists())
		self.assertFalse(Appointment.objects.filter(pk=self.future_appointment.id).exists())

	def test_admin_delete_via_destroy_endpoint_uses_archive_policy(self):
		self.client.force_authenticate(user=self.admin_user)

		response = self.client.delete(f'/api/patients/{self.patient_profile.id}/')

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.patient_profile.refresh_from_db()
		self.assertTrue(self.patient_profile.is_account_deleted)

	def test_non_admin_cannot_delete_patient_account(self):
		self.client.force_authenticate(user=self.patient_user)

		response = self.client.post(
			f'/api/patients/{self.patient_profile.id}/delete-account/',
			{},
			format='json',
		)

		self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

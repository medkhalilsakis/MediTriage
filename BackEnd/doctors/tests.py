from rest_framework import status
from rest_framework.test import APITestCase

from authentication.models import CustomUser
from doctors.models import DoctorLeave, DoctorProfile
from notifications.models import Notification


class DoctorLeaveRequestTests(APITestCase):
	def setUp(self):
		self.doctor_user = self._create_user('doctor-leave@meditriage.test', CustomUser.Role.DOCTOR)
		self.admin_user = self._create_user('admin-leave@meditriage.test', CustomUser.Role.ADMIN, is_staff=True)

		self.profile = DoctorProfile.objects.create(
			user=self.doctor_user,
			specialization='General specialist',
			department=DoctorProfile.Department.GENERAL_MEDICINE,
			license_number='DOC-LEAVE-001',
		)

	def test_doctor_leave_is_created_as_pending(self):
		self.client.force_authenticate(user=self.doctor_user)
		response = self.client.post(
			'/api/doctors/leaves/',
			{
				'start_date': '2026-05-01',
				'end_date': '2026-05-02',
				'reason': 'Annual leave',
			},
			format='json',
		)

		self.assertEqual(response.status_code, status.HTTP_201_CREATED)
		self.assertEqual(response.data['status'], DoctorLeave.Status.PENDING)
		self.assertFalse(response.data['is_active'])

	def test_doctor_without_profile_gets_validation_error_not_500(self):
		orphan_doctor = self._create_user('orphan-doctor@meditriage.test', CustomUser.Role.DOCTOR)
		self.client.force_authenticate(user=orphan_doctor)

		response = self.client.post(
			'/api/doctors/leaves/',
			{
				'start_date': '2026-05-01',
				'end_date': '2026-05-01',
			},
			format='json',
		)

		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
		self.assertIn('doctor', response.data)

	def test_admin_approval_sends_notification_to_doctor(self):
		self.client.force_authenticate(user=self.doctor_user)
		create_response = self.client.post(
			'/api/doctors/leaves/',
			{
				'start_date': '2026-05-03',
				'end_date': '2026-05-04',
				'reason': 'Family leave',
			},
			format='json',
		)
		self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)

		self.client.force_authenticate(user=self.admin_user)
		approve_response = self.client.post(
			f"/api/doctors/leaves/{create_response.data['id']}/approve/",
			{'review_note': 'Approved by administration.'},
			format='json',
		)

		self.assertEqual(approve_response.status_code, status.HTTP_200_OK)
		self.assertTrue(
			Notification.objects.filter(
				recipient=self.doctor_user,
				title='Leave request approved',
				notification_type=Notification.Type.SYSTEM,
			).exists()
		)

	def test_admin_rejection_sends_notification_to_doctor(self):
		self.client.force_authenticate(user=self.doctor_user)
		create_response = self.client.post(
			'/api/doctors/leaves/',
			{
				'start_date': '2026-05-05',
				'end_date': '2026-05-06',
				'reason': 'Personal leave',
			},
			format='json',
		)
		self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)

		self.client.force_authenticate(user=self.admin_user)
		reject_response = self.client.post(
			f"/api/doctors/leaves/{create_response.data['id']}/reject/",
			{'review_note': 'Insufficient staffing.'},
			format='json',
		)

		self.assertEqual(reject_response.status_code, status.HTTP_200_OK)
		self.assertTrue(
			Notification.objects.filter(
				recipient=self.doctor_user,
				title='Leave request rejected',
				notification_type=Notification.Type.SYSTEM,
			).exists()
		)

	def test_doctor_can_cancel_leave_request_anytime(self):
		self.client.force_authenticate(user=self.doctor_user)
		create_response = self.client.post(
			'/api/doctors/leaves/',
			{
				'start_date': '2026-06-01',
				'end_date': '2026-06-03',
				'reason': 'Travel',
			},
			format='json',
		)
		self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)

		cancel_pending_response = self.client.post(
			f"/api/doctors/leaves/{create_response.data['id']}/cancel/",
			{},
			format='json',
		)
		self.assertEqual(cancel_pending_response.status_code, status.HTTP_200_OK)
		self.assertEqual(cancel_pending_response.data['status'], DoctorLeave.Status.CANCELLED)
		self.assertFalse(cancel_pending_response.data['is_active'])

		create_response = self.client.post(
			'/api/doctors/leaves/',
			{
				'start_date': '2026-06-10',
				'end_date': '2026-06-11',
				'reason': 'Conference',
			},
			format='json',
		)
		self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)

		self.client.force_authenticate(user=self.admin_user)
		approve_response = self.client.post(
			f"/api/doctors/leaves/{create_response.data['id']}/approve/",
			{},
			format='json',
		)
		self.assertEqual(approve_response.status_code, status.HTTP_200_OK)

		self.client.force_authenticate(user=self.doctor_user)
		cancel_approved_response = self.client.post(
			f"/api/doctors/leaves/{create_response.data['id']}/cancel/",
			{},
			format='json',
		)
		self.assertEqual(cancel_approved_response.status_code, status.HTTP_200_OK)
		self.assertEqual(cancel_approved_response.data['status'], DoctorLeave.Status.CANCELLED)
		self.assertFalse(cancel_approved_response.data['is_active'])

	@staticmethod
	def _create_user(email, role, is_staff=False):
		return CustomUser.objects.create_user(
			email=email,
			username=email.split('@')[0],
			password='StrongPass123!',
			role=role,
			is_staff=is_staff,
			is_active=True,
		)


class DoctorAccountLifecycleTests(APITestCase):
	def setUp(self):
		self.admin_user = CustomUser.objects.create_user(
			email='admin-users@meditriage.test',
			username='admin-users',
			password='StrongPass123!',
			role=CustomUser.Role.ADMIN,
			is_staff=True,
			is_active=True,
		)
		self.doctor_user = CustomUser.objects.create_user(
			email='doctor-users@meditriage.test',
			username='doctor-users',
			password='StrongPass123!',
			role=CustomUser.Role.DOCTOR,
			is_active=True,
		)
		self.doctor_profile = DoctorProfile.objects.create(
			user=self.doctor_user,
			specialization='General specialist',
			department=DoctorProfile.Department.GENERAL_MEDICINE,
			license_number='DOC-USERS-001',
		)

	def test_admin_can_deactivate_and_reactivate_doctor_account(self):
		self.client.force_authenticate(user=self.admin_user)

		deactivate_response = self.client.post(
			f'/api/doctors/profiles/{self.doctor_profile.id}/deactivate/',
			{},
			format='json',
		)
		self.assertEqual(deactivate_response.status_code, status.HTTP_200_OK)
		self.assertFalse(deactivate_response.data['is_active'])

		self.doctor_user.refresh_from_db()
		self.assertFalse(self.doctor_user.is_active)

		reactivate_response = self.client.post(
			f'/api/doctors/profiles/{self.doctor_profile.id}/reactivate/',
			{},
			format='json',
		)
		self.assertEqual(reactivate_response.status_code, status.HTTP_200_OK)
		self.assertTrue(reactivate_response.data['is_active'])

		self.doctor_user.refresh_from_db()
		self.assertTrue(self.doctor_user.is_active)

	def test_non_admin_cannot_toggle_doctor_account(self):
		self.client.force_authenticate(user=self.doctor_user)

		response = self.client.post(
			f'/api/doctors/profiles/{self.doctor_profile.id}/deactivate/',
			{},
			format='json',
		)
		self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

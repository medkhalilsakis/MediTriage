from datetime import datetime, timedelta

from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from authentication.models import CustomUser
from doctors.models import DoctorLeave, DoctorProfile
from notifications.models import Notification
from patients.models import PatientProfile

from .models import Appointment, AppointmentAdvanceOffer
from .workflows import auto_postpone_unhandled_appointments


@override_settings(TIME_ZONE='UTC', USE_TZ=True)
class AppointmentWorkflowTests(APITestCase):
	def setUp(self):
		self.patient_user = self._create_user('patient1@meditriage.test', CustomUser.Role.PATIENT)
		self.patient_profile = PatientProfile.objects.create(user=self.patient_user)

		self.patient2_user = self._create_user('patient2@meditriage.test', CustomUser.Role.PATIENT)
		self.patient2_profile = PatientProfile.objects.create(user=self.patient2_user)

		self.doctor_user_1 = self._create_user('doctor1@meditriage.test', CustomUser.Role.DOCTOR)
		self.doctor_1 = self._create_doctor(self.doctor_user_1, 'LIC-001', DoctorProfile.Department.GENERAL_MEDICINE)

		self.doctor_user_2 = self._create_user('doctor2@meditriage.test', CustomUser.Role.DOCTOR)
		self.doctor_2 = self._create_doctor(self.doctor_user_2, 'LIC-002', DoctorProfile.Department.GENERAL_MEDICINE)

		self.doctor_user_3 = self._create_user('doctor3@meditriage.test', CustomUser.Role.DOCTOR)
		self.doctor_3 = self._create_doctor(self.doctor_user_3, 'LIC-003', DoctorProfile.Department.CARDIOLOGY)

		self.admin_user = self._create_user('admin@meditriage.test', CustomUser.Role.ADMIN, is_staff=True)

	def test_patient_booking_auto_confirmed_and_skips_doctor_leave(self):
		DoctorLeave.objects.create(
			doctor=self.doctor_1,
			start_date=timezone.localdate(),
			end_date=timezone.localdate() + timedelta(days=30),
			reason='Vacation',
			status=DoctorLeave.Status.APPROVED,
			is_active=True,
			created_by=self.doctor_user_1,
		)

		self.client.force_authenticate(user=self.patient_user)
		response = self.client.post(
			'/api/appointments/',
			{
				'department': Appointment.Department.GENERAL_MEDICINE,
				'reason': 'Persistent fever and fatigue',
				'urgency_level': Appointment.UrgencyLevel.MEDIUM,
			},
			format='json',
		)

		self.assertEqual(response.status_code, status.HTTP_201_CREATED)
		appointment = Appointment.objects.get(pk=response.data['id'])
		self.assertEqual(appointment.status, Appointment.Status.CONFIRMED)
		self.assertEqual(appointment.doctor_id, self.doctor_2.id)

	def test_doctor_leave_reassigns_appointments_to_available_doctors(self):
		slot = self._dt(days=3, hour=10)
		appointment = Appointment.objects.create(
			patient=self.patient_profile,
			doctor=self.doctor_1,
			scheduled_at=slot,
			status=Appointment.Status.CONFIRMED,
			reason='Routine check',
			department=self.doctor_1.department,
		)

		self.client.force_authenticate(user=self.doctor_user_1)
		response = self.client.post(
			'/api/doctors/leaves/',
			{
				'start_date': slot.date().isoformat(),
				'end_date': slot.date().isoformat(),
				'reason': 'Urgent leave',
			},
			format='json',
		)

		self.assertEqual(response.status_code, status.HTTP_201_CREATED)
		self.assertEqual(response.data['status'], DoctorLeave.Status.PENDING)
		self.assertFalse(response.data['is_active'])

		appointment.refresh_from_db()
		self.assertEqual(appointment.doctor_id, self.doctor_1.id)

		self.client.force_authenticate(user=self.admin_user)
		approve_response = self.client.post(
			f"/api/doctors/leaves/{response.data['id']}/approve/",
			{},
			format='json',
		)
		self.assertEqual(approve_response.status_code, status.HTTP_200_OK)

		appointment.refresh_from_db()
		self.assertEqual(appointment.doctor_id, self.doctor_2.id)
		self.assertEqual(appointment.status, Appointment.Status.CONFIRMED)
		self.assertTrue(Notification.objects.filter(recipient=self.patient_user, title='Appointment reassigned').exists())

	def test_doctor_leave_postpones_when_no_replacement_available(self):
		# Remove second doctor to force postponement flow.
		self.doctor_2.delete()
		self.doctor_3.delete()

		slot = self._dt(days=2, hour=11)
		appointment = Appointment.objects.create(
			patient=self.patient_profile,
			doctor=self.doctor_1,
			scheduled_at=slot,
			status=Appointment.Status.CONFIRMED,
			reason='Follow-up',
			department=self.doctor_1.department,
		)

		self.client.force_authenticate(user=self.doctor_user_1)
		response = self.client.post(
			'/api/doctors/leaves/',
			{
				'start_date': slot.date().isoformat(),
				'end_date': slot.date().isoformat(),
				'reason': 'Unavailable',
			},
			format='json',
		)

		self.assertEqual(response.status_code, status.HTTP_201_CREATED)
		self.assertEqual(response.data['status'], DoctorLeave.Status.PENDING)

		self.client.force_authenticate(user=self.admin_user)
		approve_response = self.client.post(
			f"/api/doctors/leaves/{response.data['id']}/approve/",
			{},
			format='json',
		)
		self.assertEqual(approve_response.status_code, status.HTTP_200_OK)

		appointment.refresh_from_db()
		self.assertEqual(appointment.doctor_id, self.doctor_1.id)
		self.assertGreater(appointment.scheduled_at.date(), slot.date())
		self.assertEqual(appointment.status, Appointment.Status.CONFIRMED)
		self.assertTrue(Notification.objects.filter(recipient=self.patient_user, title='Appointment postponed').exists())

	def test_rejected_leave_does_not_impact_appointments(self):
		slot = self._dt(days=6, hour=11)
		appointment = Appointment.objects.create(
			patient=self.patient_profile,
			doctor=self.doctor_1,
			scheduled_at=slot,
			status=Appointment.Status.CONFIRMED,
			reason='Needs doctor assignment unchanged',
			department=self.doctor_1.department,
		)

		self.client.force_authenticate(user=self.doctor_user_1)
		create_response = self.client.post(
			'/api/doctors/leaves/',
			{
				'start_date': slot.date().isoformat(),
				'end_date': slot.date().isoformat(),
				'reason': 'Potential leave',
			},
			format='json',
		)
		self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)

		self.client.force_authenticate(user=self.admin_user)
		reject_response = self.client.post(
			f"/api/doctors/leaves/{create_response.data['id']}/reject/",
			{'review_note': 'Service demand too high this week.'},
			format='json',
		)
		self.assertEqual(reject_response.status_code, status.HTTP_200_OK)
		self.assertEqual(reject_response.data['status'], DoctorLeave.Status.REJECTED)
		self.assertFalse(reject_response.data['is_active'])

		appointment.refresh_from_db()
		self.assertEqual(appointment.doctor_id, self.doctor_1.id)
		self.assertEqual(appointment.scheduled_at, slot)

	def test_patient_cancellation_creates_advance_offer_and_accept_flow(self):
		slot_one = self._dt(days=4, hour=9)
		slot_two = self._dt(days=4, hour=10)

		first_appointment = Appointment.objects.create(
			patient=self.patient_profile,
			doctor=self.doctor_1,
			scheduled_at=slot_one,
			status=Appointment.Status.CONFIRMED,
			reason='Initial slot',
			department=self.doctor_1.department,
		)
		second_appointment = Appointment.objects.create(
			patient=self.patient2_profile,
			doctor=self.doctor_1,
			scheduled_at=slot_two,
			status=Appointment.Status.CONFIRMED,
			reason='Later slot',
			department=self.doctor_1.department,
		)

		self.client.force_authenticate(user=self.patient_user)
		cancel_response = self.client.patch(
			f'/api/appointments/{first_appointment.id}/',
			{'status': Appointment.Status.CANCELLED},
			format='json',
		)
		self.assertEqual(cancel_response.status_code, status.HTTP_200_OK)

		offer = AppointmentAdvanceOffer.objects.get(appointment=second_appointment)
		self.assertEqual(offer.status, AppointmentAdvanceOffer.Status.PENDING)
		self.assertEqual(offer.offered_slot, slot_one)

		self.client.force_authenticate(user=self.patient2_user)
		accept_response = self.client.post(
			f'/api/appointments/advance-offers/{offer.id}/respond/',
			{'decision': 'accept'},
			format='json',
		)
		self.assertEqual(accept_response.status_code, status.HTTP_200_OK)

		second_appointment.refresh_from_db()
		offer.refresh_from_db()
		self.assertEqual(second_appointment.scheduled_at, slot_one)
		self.assertEqual(offer.status, AppointmentAdvanceOffer.Status.ACCEPTED)

	def test_doctor_can_reassign_to_other_department(self):
		slot = self._dt(days=5, hour=14)
		appointment = Appointment.objects.create(
			patient=self.patient_profile,
			doctor=self.doctor_1,
			scheduled_at=slot,
			status=Appointment.Status.CONFIRMED,
			reason='Cross-department reassignment',
			department=self.doctor_1.department,
		)

		self.client.force_authenticate(user=self.doctor_user_1)
		response = self.client.post(
			f'/api/appointments/{appointment.id}/reassign/',
			{
				'doctor_id': self.doctor_3.id,
				'scheduled_at': slot.isoformat(),
			},
			format='json',
		)

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		appointment.refresh_from_db()
		self.assertEqual(appointment.doctor_id, self.doctor_3.id)
		self.assertEqual(appointment.department, self.doctor_3.department)

	def test_patient_auto_booking_stays_within_operating_hours(self):
		self.client.force_authenticate(user=self.patient_user)
		response = self.client.post(
			'/api/appointments/',
			{
				'department': Appointment.Department.GENERAL_MEDICINE,
				'reason': 'Need consultation inside daytime window',
				'urgency_level': Appointment.UrgencyLevel.MEDIUM,
			},
			format='json',
		)

		self.assertEqual(response.status_code, status.HTTP_201_CREATED)
		appointment = Appointment.objects.get(pk=response.data['id'])
		local_slot = timezone.localtime(appointment.scheduled_at)
		self.assertGreaterEqual(local_slot.hour, 8)
		self.assertLess(local_slot.hour, 16)

	def test_doctor_daily_endpoint_accepts_date_query(self):
		slot = self._dt(days=2, hour=10)
		appointment = Appointment.objects.create(
			patient=self.patient_profile,
			doctor=self.doctor_1,
			scheduled_at=slot,
			status=Appointment.Status.CONFIRMED,
			reason='Date-filtered schedule check',
			department=self.doctor_1.department,
		)

		self.client.force_authenticate(user=self.doctor_user_1)
		response = self.client.get(f'/api/appointments/today/?date={slot.date().isoformat()}')

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		items = response.data.get('results', response.data)
		self.assertTrue(any(item['id'] == appointment.id for item in items))

	def test_doctor_can_mark_appointment_completed(self):
		slot = self._dt(days=2, hour=9)
		appointment = Appointment.objects.create(
			patient=self.patient_profile,
			doctor=self.doctor_1,
			scheduled_at=slot,
			status=Appointment.Status.CONFIRMED,
			reason='Consultation completed in doctor workflow',
			department=self.doctor_1.department,
		)

		self.client.force_authenticate(user=self.doctor_user_1)
		response = self.client.post(f'/api/appointments/{appointment.id}/complete/', {}, format='json')

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data['status'], Appointment.Status.COMPLETED)

		appointment.refresh_from_db()
		self.assertEqual(appointment.status, Appointment.Status.COMPLETED)
		self.assertTrue(appointment.last_staff_action_at)

	def test_hourly_capacity_blocks_more_than_two_patients_per_hour(self):
		target_day = timezone.localdate() + timedelta(days=3)
		slot_800 = timezone.make_aware(datetime(target_day.year, target_day.month, target_day.day, 8, 0))
		slot_845 = timezone.make_aware(datetime(target_day.year, target_day.month, target_day.day, 8, 45))
		slot_930 = timezone.make_aware(datetime(target_day.year, target_day.month, target_day.day, 9, 30))

		Appointment.objects.create(
			patient=self.patient_profile,
			doctor=self.doctor_1,
			scheduled_at=slot_800,
			status=Appointment.Status.CONFIRMED,
			reason='First in hour',
			department=self.doctor_1.department,
		)
		Appointment.objects.create(
			patient=self.patient2_profile,
			doctor=self.doctor_1,
			scheduled_at=slot_845,
			status=Appointment.Status.CONFIRMED,
			reason='Second in hour (legacy time)',
			department=self.doctor_1.department,
		)
		third_appointment = Appointment.objects.create(
			patient=self.patient_profile,
			doctor=self.doctor_1,
			scheduled_at=slot_930,
			status=Appointment.Status.CONFIRMED,
			reason='Candidate third in same hour',
			department=self.doctor_1.department,
		)

		self.client.force_authenticate(user=self.doctor_user_1)
		response = self.client.post(
			f'/api/appointments/{third_appointment.id}/delay/',
			{
				'scheduled_at': slot_800.replace(minute=30).isoformat(),
			},
			format='json',
		)

		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
		self.assertIn('scheduled_at', response.data)

	def test_auto_postpone_unhandled_after_one_hour(self):
		slot = self._past_slot(hour=10)
		appointment = Appointment.objects.create(
			patient=self.patient_profile,
			doctor=self.doctor_1,
			scheduled_at=slot,
			status=Appointment.Status.CONFIRMED,
			reason='No staff action yet',
			department=self.doctor_1.department,
		)

		result = auto_postpone_unhandled_appointments(now=slot + timedelta(hours=1, minutes=5))
		self.assertEqual(result['postponed'], 1)

		appointment.refresh_from_db()
		expected_date = slot.date() + timedelta(days=1)
		if expected_date.weekday() == 6:
			expected_date += timedelta(days=1)

		self.assertEqual(appointment.scheduled_at.date(), expected_date)
		self.assertEqual(timezone.localtime(appointment.scheduled_at).hour, timezone.localtime(slot).hour)
		self.assertTrue(
			Notification.objects.filter(
				recipient=self.patient_user,
				title='Appointment auto-postponed',
			).exists()
		)

	def test_auto_postpone_skips_sunday_by_delaying_two_days(self):
		today = timezone.localdate()
		days_since_saturday = (today.weekday() - 5) % 7
		if days_since_saturday == 0:
			days_since_saturday = 7
		saturday_date = today - timedelta(days=days_since_saturday)

		saturday_slot = timezone.make_aware(
			datetime(saturday_date.year, saturday_date.month, saturday_date.day, 10, 0, 0),
			timezone.get_current_timezone(),
		)
		appointment = Appointment.objects.create(
			patient=self.patient_profile,
			doctor=self.doctor_1,
			scheduled_at=saturday_slot,
			status=Appointment.Status.CONFIRMED,
			reason='Saturday appointment without action',
			department=self.doctor_1.department,
		)

		auto_postpone_unhandled_appointments(now=saturday_slot + timedelta(hours=2))
		appointment.refresh_from_db()

		expected_monday = saturday_date + timedelta(days=2)
		self.assertEqual(appointment.scheduled_at.date(), expected_monday)
		self.assertEqual(appointment.scheduled_at.weekday(), 0)

	def test_auto_postpone_does_not_run_if_staff_action_exists(self):
		slot = self._past_slot(hour=11)
		appointment = Appointment.objects.create(
			patient=self.patient_profile,
			doctor=self.doctor_1,
			scheduled_at=slot,
			status=Appointment.Status.CONFIRMED,
			reason='Already handled by doctor',
			department=self.doctor_1.department,
			last_staff_action_at=slot + timedelta(minutes=10),
		)

		result = auto_postpone_unhandled_appointments(now=slot + timedelta(hours=2))
		self.assertEqual(result['postponed'], 0)

		appointment.refresh_from_db()
		self.assertEqual(appointment.scheduled_at, slot)

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

	@staticmethod
	def _create_doctor(user, license_number, department):
		return DoctorProfile.objects.create(
			user=user,
			specialization='General specialist',
			department=department,
			license_number=license_number,
			years_of_experience=7,
		)

	@staticmethod
	def _dt(days, hour, minute=0):
		target = timezone.now() + timedelta(days=days)
		if target.weekday() == 6:
			target = target + timedelta(days=1)
		naive = datetime(target.year, target.month, target.day, hour, minute, 0)
		return timezone.make_aware(naive, timezone.get_current_timezone())

	@staticmethod
	def _past_slot(hour, minute=0):
		target = timezone.now() - timedelta(days=2)
		if target.weekday() == 6:
			target = target - timedelta(days=1)
		naive = datetime(target.year, target.month, target.day, hour, minute, 0)
		return timezone.make_aware(naive, timezone.get_current_timezone())

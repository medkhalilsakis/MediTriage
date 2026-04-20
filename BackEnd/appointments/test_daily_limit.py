from datetime import datetime, timedelta
from unittest.mock import patch

from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from authentication.models import CustomUser
from doctors.models import DoctorProfile
from patients.models import PatientProfile

from .models import Appointment


@override_settings(TIME_ZONE='UTC', USE_TZ=True)
class AppointmentDailyLimitTests(APITestCase):
    def setUp(self):
        self.patient_user = self._create_user('daily-patient@meditriage.test', CustomUser.Role.PATIENT)
        self.patient_profile = PatientProfile.objects.create(user=self.patient_user)

        self.doctor_user_1 = self._create_user('daily-doctor1@meditriage.test', CustomUser.Role.DOCTOR)
        self.doctor_1 = self._create_doctor(
            user=self.doctor_user_1,
            license_number='DAILY-LIC-001',
            department=DoctorProfile.Department.GENERAL_MEDICINE,
        )

        self.doctor_user_2 = self._create_user('daily-doctor2@meditriage.test', CustomUser.Role.DOCTOR)
        self.doctor_2 = self._create_doctor(
            user=self.doctor_user_2,
            license_number='DAILY-LIC-002',
            department=DoctorProfile.Department.GENERAL_MEDICINE,
        )

        self.admin_user = self._create_user(
            'daily-admin@meditriage.test',
            CustomUser.Role.ADMIN,
            is_staff=True,
        )

    def test_admin_cannot_create_second_same_day_appointment_for_patient(self):
        first_slot = self._slot(days=3, hour=9)
        second_slot = self._slot(days=3, hour=11)

        Appointment.objects.create(
            patient=self.patient_profile,
            doctor=self.doctor_1,
            scheduled_at=first_slot,
            status=Appointment.Status.CONFIRMED,
            reason='Initial same-day appointment',
            urgency_level=Appointment.UrgencyLevel.MEDIUM,
            department=self.doctor_1.department,
        )

        self.client.force_authenticate(user=self.admin_user)
        response = self.client.post(
            '/api/appointments/',
            {
                'patient': self.patient_profile.id,
                'doctor': self.doctor_2.id,
                'scheduled_at': second_slot.isoformat(),
                'reason': 'Attempted second same-day appointment',
                'urgency_level': Appointment.UrgencyLevel.MEDIUM,
                'department': self.doctor_2.department,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('scheduled_at', response.data)

    def test_doctor_cannot_reschedule_patient_to_day_with_existing_appointment(self):
        existing_day_slot = self._slot(days=4, hour=9)
        other_day_slot = self._slot(days=5, hour=10)

        Appointment.objects.create(
            patient=self.patient_profile,
            doctor=self.doctor_1,
            scheduled_at=existing_day_slot,
            status=Appointment.Status.CONFIRMED,
            reason='Existing appointment day',
            urgency_level=Appointment.UrgencyLevel.MEDIUM,
            department=self.doctor_1.department,
        )
        movable_appointment = Appointment.objects.create(
            patient=self.patient_profile,
            doctor=self.doctor_2,
            scheduled_at=other_day_slot,
            status=Appointment.Status.CONFIRMED,
            reason='Appointment to be delayed',
            urgency_level=Appointment.UrgencyLevel.MEDIUM,
            department=self.doctor_2.department,
        )

        self.client.force_authenticate(user=self.doctor_user_2)
        response = self.client.post(
            f'/api/appointments/{movable_appointment.id}/delay/',
            {
                'scheduled_at': self._slot(days=4, hour=11).isoformat(),
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('scheduled_at', response.data)

        movable_appointment.refresh_from_db()
        self.assertEqual(movable_appointment.scheduled_at, other_day_slot)

    @patch('appointments.scheduling.assign_doctor_and_slot')
    def test_patient_auto_booking_moves_to_next_available_day_when_same_day_conflict(
        self,
        mocked_assign_doctor_and_slot,
    ):
        first_slot = self._slot(days=3, hour=9)
        conflicting_slot = self._slot(days=3, hour=11)
        next_day_slot = self._slot(days=4, hour=10)

        Appointment.objects.create(
            patient=self.patient_profile,
            doctor=self.doctor_1,
            scheduled_at=first_slot,
            status=Appointment.Status.CONFIRMED,
            reason='Existing same-day appointment',
            urgency_level=Appointment.UrgencyLevel.MEDIUM,
            department=self.doctor_1.department,
        )

        mocked_assign_doctor_and_slot.side_effect = [
            (
                self.doctor_2,
                conflicting_slot,
                self.doctor_2.department,
            ),
            (
                self.doctor_2,
                next_day_slot,
                self.doctor_2.department,
            ),
        ]

        self.client.force_authenticate(user=self.patient_user)
        response = self.client.post(
            '/api/appointments/',
            {
                'reason': 'New symptoms that require consultation',
                'urgency_level': Appointment.UrgencyLevel.MEDIUM,
                'department': Appointment.Department.GENERAL_MEDICINE,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Appointment.objects.filter(patient=self.patient_profile).count(), 2)
        self.assertIn('booking_notice', response.data)

        created = Appointment.objects.get(pk=response.data['id'])
        self.assertEqual(created.scheduled_at, next_day_slot)
        self.assertNotEqual(created.scheduled_at.date(), first_slot.date())

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
            years_of_experience=8,
        )

    @staticmethod
    def _slot(days, hour, minute=0):
        target = timezone.now() + timedelta(days=days)
        if target.weekday() == 6:
            target = target + timedelta(days=1)
        naive = datetime(target.year, target.month, target.day, hour, minute, 0)
        return timezone.make_aware(naive, timezone.get_current_timezone())

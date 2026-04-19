from datetime import timedelta

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from appointments.models import Appointment
from authentication.models import CustomUser
from doctors.models import DoctorProfile
from patients.models import PatientProfile


class MessagingFlowTests(APITestCase):
    def setUp(self):
        self.patient_user = CustomUser.objects.create_user(
            email='patient.messaging@example.com',
            password='pass1234',
            role=CustomUser.Role.PATIENT,
            username='patient_messaging',
        )
        self.patient_profile = PatientProfile.objects.create(user=self.patient_user)

        self.doctor_user = CustomUser.objects.create_user(
            email='doctor.messaging@example.com',
            password='pass1234',
            role=CustomUser.Role.DOCTOR,
            username='doctor_messaging',
        )
        self.doctor_profile = DoctorProfile.objects.create(
            user=self.doctor_user,
            specialization='General Medicine',
            department=DoctorProfile.Department.GENERAL_MEDICINE,
            license_number='LIC-MSG-001',
            years_of_experience=8,
        )

        self.other_doctor_user = CustomUser.objects.create_user(
            email='other.doctor.messaging@example.com',
            password='pass1234',
            role=CustomUser.Role.DOCTOR,
            username='other_doctor_messaging',
        )
        self.other_doctor_profile = DoctorProfile.objects.create(
            user=self.other_doctor_user,
            specialization='Cardiology',
            department=DoctorProfile.Department.CARDIOLOGY,
            license_number='LIC-MSG-002',
            years_of_experience=10,
        )

        self.admin_user = CustomUser.objects.create_user(
            email='admin.messaging@example.com',
            password='pass1234',
            role=CustomUser.Role.ADMIN,
            username='admin_messaging',
            is_staff=True,
        )

        Appointment.objects.create(
            patient=self.patient_profile,
            doctor=self.doctor_profile,
            scheduled_at=timezone.now() + timedelta(days=1),
            status=Appointment.Status.CONFIRMED,
            urgency_level=Appointment.UrgencyLevel.MEDIUM,
            department=Appointment.Department.GENERAL_MEDICINE,
            reason='Messaging eligibility appointment',
        )

    def test_patient_contacts_include_assigned_doctor_and_admin_only(self):
        self.client.force_authenticate(user=self.patient_user)

        response = self.client.get('/api/messaging/contacts/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        emails = {item['email'] for item in response.data['results']}
        self.assertIn(self.doctor_user.email, emails)
        self.assertIn(self.admin_user.email, emails)
        self.assertNotIn(self.other_doctor_user.email, emails)

    def test_patient_cannot_open_conversation_with_unassigned_doctor(self):
        self.client.force_authenticate(user=self.patient_user)

        response = self.client.post(
            '/api/messaging/conversations/',
            {'recipient_id': self.other_doctor_user.id},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_patient_and_assigned_doctor_can_exchange_messages(self):
        self.client.force_authenticate(user=self.patient_user)

        open_response = self.client.post(
            '/api/messaging/conversations/',
            {'recipient_id': self.doctor_user.id},
            format='json',
        )
        self.assertIn(open_response.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED])

        conversation_id = open_response.data['conversation']['id']

        send_response = self.client.post(
            f'/api/messaging/conversations/{conversation_id}/messages/',
            {'content': 'Hello doctor, I need clarification about treatment.'},
            format='json',
        )
        self.assertEqual(send_response.status_code, status.HTTP_201_CREATED)

        self.client.force_authenticate(user=self.doctor_user)
        inbox_response = self.client.get(f'/api/messaging/conversations/{conversation_id}/messages/')
        self.assertEqual(inbox_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(inbox_response.data['messages']), 1)
        self.assertEqual(
            inbox_response.data['messages'][0]['content'],
            'Hello doctor, I need clarification about treatment.',
        )

    def test_presence_heartbeat_updates_online_status(self):
        self.client.force_authenticate(user=self.doctor_user)
        heartbeat_response = self.client.post('/api/messaging/presence/heartbeat/', {'is_online': True}, format='json')
        self.assertEqual(heartbeat_response.status_code, status.HTTP_200_OK)

        self.client.force_authenticate(user=self.patient_user)
        contacts_response = self.client.get('/api/messaging/contacts/')
        self.assertEqual(contacts_response.status_code, status.HTTP_200_OK)

        doctor_contact = next(
            (item for item in contacts_response.data['results'] if item['id'] == self.doctor_user.id),
            None,
        )
        self.assertIsNotNone(doctor_contact)
        self.assertTrue(doctor_contact['is_online'])

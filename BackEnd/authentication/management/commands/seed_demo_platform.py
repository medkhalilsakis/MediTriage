from datetime import time, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from appointments.models import Appointment
from chatbot.ai_service import build_health_chat_response
from chatbot.models import ChatbotMessage, ChatbotSession
from doctors.models import DoctorAvailabilitySlot, DoctorLeave, DoctorProfile
from follow_up.models import FollowUp, FollowUpAlert
from medical_records.models import Consultation, MedicalDocumentRequest, MedicalRecord
from notifications.models import Notification
from patients.models import PatientProfile
from prescriptions.models import Prescription, PrescriptionItem

from authentication.models import CustomUser

DEMO_EMAIL_DOMAIN = "demo.meditriage.local"
DEFAULT_PASSWORD = "DemoPass123!"

DOCTOR_BLUEPRINTS = [
    {
        "slug": "dr_amina",
        "first_name": "Amina",
        "last_name": "Bouzid",
        "specialization": "General practitioner",
        "department": DoctorProfile.Department.GENERAL_MEDICINE,
        "license_number": "DEMO-DOC-001",
        "years_of_experience": 9,
        "consultation_fee": "2500.00",
        "bio": "Coordinates first-line triage and chronic care follow-up.",
    },
    {
        "slug": "dr_yacine",
        "first_name": "Yacine",
        "last_name": "Ferhat",
        "specialization": "Cardiology specialist",
        "department": DoctorProfile.Department.CARDIOLOGY,
        "license_number": "DEMO-DOC-002",
        "years_of_experience": 12,
        "consultation_fee": "3200.00",
        "bio": "Focuses on hypertension and chest pain evaluation.",
    },
    {
        "slug": "dr_samira",
        "first_name": "Samira",
        "last_name": "Khelifi",
        "specialization": "Respiratory specialist",
        "department": DoctorProfile.Department.RESPIRATORY,
        "license_number": "DEMO-DOC-003",
        "years_of_experience": 11,
        "consultation_fee": "3000.00",
        "bio": "Manages asthma and persistent respiratory symptoms.",
    },
    {
        "slug": "dr_karim",
        "first_name": "Karim",
        "last_name": "Mansouri",
        "specialization": "Neurology specialist",
        "department": DoctorProfile.Department.NEUROLOGY,
        "license_number": "DEMO-DOC-004",
        "years_of_experience": 10,
        "consultation_fee": "3400.00",
        "bio": "Handles migraines, dizziness, and neurological complaints.",
    },
    {
        "slug": "dr_lyna",
        "first_name": "Lyna",
        "last_name": "Saadi",
        "specialization": "Dermatology specialist",
        "department": DoctorProfile.Department.DERMATOLOGY,
        "license_number": "DEMO-DOC-005",
        "years_of_experience": 8,
        "consultation_fee": "2900.00",
        "bio": "Treats dermatologic disorders and follow-up prevention plans.",
    },
]

PATIENT_BLUEPRINTS = [
    {
        "slug": "patient01",
        "first_name": "Nadia",
        "last_name": "Benali",
        "gender": PatientProfile.Gender.FEMALE,
        "blood_group": PatientProfile.BloodGroup.A_POS,
        "allergies": "None",
    },
    {
        "slug": "patient02",
        "first_name": "Walid",
        "last_name": "Ait",
        "gender": PatientProfile.Gender.MALE,
        "blood_group": PatientProfile.BloodGroup.O_POS,
        "allergies": "Pollen",
    },
    {
        "slug": "patient03",
        "first_name": "Sara",
        "last_name": "Kaci",
        "gender": PatientProfile.Gender.FEMALE,
        "blood_group": PatientProfile.BloodGroup.B_POS,
        "allergies": "Penicillin",
    },
    {
        "slug": "patient04",
        "first_name": "Yanis",
        "last_name": "Mokhtar",
        "gender": PatientProfile.Gender.MALE,
        "blood_group": PatientProfile.BloodGroup.A_NEG,
        "allergies": "None",
    },
    {
        "slug": "patient05",
        "first_name": "Ines",
        "last_name": "Berrahal",
        "gender": PatientProfile.Gender.FEMALE,
        "blood_group": PatientProfile.BloodGroup.AB_POS,
        "allergies": "Dust",
    },
    {
        "slug": "patient06",
        "first_name": "Hamza",
        "last_name": "Drici",
        "gender": PatientProfile.Gender.MALE,
        "blood_group": PatientProfile.BloodGroup.O_NEG,
        "allergies": "None",
    },
    {
        "slug": "patient07",
        "first_name": "Lilia",
        "last_name": "Tahar",
        "gender": PatientProfile.Gender.FEMALE,
        "blood_group": PatientProfile.BloodGroup.B_NEG,
        "allergies": "Seafood",
    },
    {
        "slug": "patient08",
        "first_name": "Riad",
        "last_name": "Zerrouki",
        "gender": PatientProfile.Gender.MALE,
        "blood_group": PatientProfile.BloodGroup.A_POS,
        "allergies": "None",
    },
    {
        "slug": "patient09",
        "first_name": "Meriem",
        "last_name": "Brahimi",
        "gender": PatientProfile.Gender.FEMALE,
        "blood_group": PatientProfile.BloodGroup.AB_NEG,
        "allergies": "Nuts",
    },
    {
        "slug": "patient10",
        "first_name": "Anis",
        "last_name": "Guerfi",
        "gender": PatientProfile.Gender.MALE,
        "blood_group": PatientProfile.BloodGroup.O_POS,
        "allergies": "None",
    },
]

APPOINTMENT_BLUEPRINTS = [
    {
        "marker": "DEMO_APPT_01",
        "patient_index": 0,
        "doctor_index": 0,
        "day_offset": -8,
        "hour": 9,
        "status": Appointment.Status.COMPLETED,
        "urgency": Appointment.UrgencyLevel.MEDIUM,
        "reason": "Recurring fatigue and mild fever",
    },
    {
        "marker": "DEMO_APPT_02",
        "patient_index": 1,
        "doctor_index": 1,
        "day_offset": -7,
        "hour": 10,
        "status": Appointment.Status.COMPLETED,
        "urgency": Appointment.UrgencyLevel.HIGH,
        "reason": "Chest discomfort under effort",
    },
    {
        "marker": "DEMO_APPT_03",
        "patient_index": 2,
        "doctor_index": 2,
        "day_offset": -6,
        "hour": 11,
        "status": Appointment.Status.COMPLETED,
        "urgency": Appointment.UrgencyLevel.MEDIUM,
        "reason": "Persistent cough over 10 days",
    },
    {
        "marker": "DEMO_APPT_04",
        "patient_index": 3,
        "doctor_index": 3,
        "day_offset": -5,
        "hour": 9,
        "status": Appointment.Status.NO_SHOW,
        "urgency": Appointment.UrgencyLevel.LOW,
        "reason": "Intermittent headaches",
    },
    {
        "marker": "DEMO_APPT_05",
        "patient_index": 4,
        "doctor_index": 4,
        "day_offset": -2,
        "hour": 14,
        "status": Appointment.Status.CANCELLED,
        "urgency": Appointment.UrgencyLevel.LOW,
        "reason": "Skin irritation follow-up",
    },
    {
        "marker": "DEMO_APPT_06",
        "patient_index": 5,
        "doctor_index": 0,
        "day_offset": 1,
        "hour": 9,
        "status": Appointment.Status.PENDING,
        "urgency": Appointment.UrgencyLevel.MEDIUM,
        "reason": "Digestive discomfort and appetite loss",
    },
    {
        "marker": "DEMO_APPT_07",
        "patient_index": 6,
        "doctor_index": 1,
        "day_offset": 1,
        "hour": 10,
        "status": Appointment.Status.CONFIRMED,
        "urgency": Appointment.UrgencyLevel.HIGH,
        "reason": "Blood pressure monitoring review",
    },
    {
        "marker": "DEMO_APPT_08",
        "patient_index": 7,
        "doctor_index": 2,
        "day_offset": 2,
        "hour": 11,
        "status": Appointment.Status.CONFIRMED,
        "urgency": Appointment.UrgencyLevel.MEDIUM,
        "reason": "Shortness of breath while climbing stairs",
    },
    {
        "marker": "DEMO_APPT_09",
        "patient_index": 8,
        "doctor_index": 3,
        "day_offset": 3,
        "hour": 14,
        "status": Appointment.Status.CONFIRMED,
        "urgency": Appointment.UrgencyLevel.LOW,
        "reason": "Migraine progression assessment",
    },
    {
        "marker": "DEMO_APPT_10",
        "patient_index": 9,
        "doctor_index": 4,
        "day_offset": 4,
        "hour": 15,
        "status": Appointment.Status.CONFIRMED,
        "urgency": Appointment.UrgencyLevel.MEDIUM,
        "reason": "Treatment review for chronic eczema",
    },
]


class Command(BaseCommand):
    help = (
        "Seed a complete demo scenario with 1 admin, 5 doctors, 10 patients, and 10 appointments. "
        "The command is idempotent and can optionally reset previous demo data."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete existing demo users (*@demo.meditriage.local) before seeding.",
        )
        parser.add_argument(
            "--password",
            default=DEFAULT_PASSWORD,
            help="Password used for all demo accounts (default: DemoPass123!).",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        password = options["password"]

        if options["reset"]:
            self._reset_demo_data()

        admin_user = self._upsert_admin(password=password)
        doctors = self._upsert_doctors(password=password)
        patients = self._upsert_patients(password=password)

        self._upsert_medical_records(patients=patients)
        self._upsert_doctor_availability(doctors=doctors)

        appointments_by_marker = self._upsert_appointments(doctors=doctors, patients=patients)
        consultations = self._upsert_consultations(appointments_by_marker=appointments_by_marker)

        self._upsert_prescriptions(consultations=consultations)
        self._upsert_follow_up(consultations=consultations)
        self._upsert_document_requests(consultations=consultations)

        self._upsert_notifications(
            admin_user=admin_user,
            doctors=doctors,
            patients=patients,
            appointments_by_marker=appointments_by_marker,
        )
        self._upsert_leave_request(admin_user=admin_user, doctor=doctors[2])
        chatbot_sessions_count = self._upsert_chatbot_conversations(patients=patients)

        self.stdout.write(self.style.SUCCESS("Demo scenario successfully loaded."))
        self.stdout.write(f"Admin account: admin@{DEMO_EMAIL_DOMAIN}")
        self.stdout.write(f"Doctors created: {len(doctors)}")
        self.stdout.write(f"Patients created: {len(patients)}")
        self.stdout.write(f"Appointments created: {len(appointments_by_marker)}")
        self.stdout.write(f"Chatbot sessions created: {chatbot_sessions_count}")
        self.stdout.write("See DEMO_PLATFORM_SCENARIO.md for the full walkthrough.")

    def _reset_demo_data(self):
        deleted, _ = CustomUser.objects.filter(email__iendswith=f"@{DEMO_EMAIL_DOMAIN}").delete()
        self.stdout.write(f"Deleted {deleted} demo-related records before reseeding.")

    def _upsert_admin(self, password):
        email = f"admin@{DEMO_EMAIL_DOMAIN}"
        user = self._upsert_user(
            email=email,
            username="demo_admin",
            role=CustomUser.Role.ADMIN,
            password=password,
            first_name="Platform",
            last_name="Admin",
            phone_number="+213555000001",
            is_staff=True,
            is_superuser=True,
        )
        return user

    def _upsert_doctors(self, password):
        doctors = []
        for index, blueprint in enumerate(DOCTOR_BLUEPRINTS, start=1):
            email = f"{blueprint['slug']}@{DEMO_EMAIL_DOMAIN}"
            user = self._upsert_user(
                email=email,
                username=f"demo_doctor_{index:02d}",
                role=CustomUser.Role.DOCTOR,
                password=password,
                first_name=blueprint["first_name"],
                last_name=blueprint["last_name"],
                phone_number=f"+2135551000{index:02d}",
            )

            doctor, _ = DoctorProfile.objects.update_or_create(
                user=user,
                defaults={
                    "specialization": blueprint["specialization"],
                    "department": blueprint["department"],
                    "license_number": blueprint["license_number"],
                    "years_of_experience": blueprint["years_of_experience"],
                    "consultation_fee": blueprint["consultation_fee"],
                    "bio": blueprint["bio"],
                },
            )
            doctors.append(doctor)

        return doctors

    def _upsert_patients(self, password):
        patients = []
        for index, blueprint in enumerate(PATIENT_BLUEPRINTS, start=1):
            email = f"{blueprint['slug']}@{DEMO_EMAIL_DOMAIN}"
            user = self._upsert_user(
                email=email,
                username=f"demo_patient_{index:02d}",
                role=CustomUser.Role.PATIENT,
                password=password,
                first_name=blueprint["first_name"],
                last_name=blueprint["last_name"],
                phone_number=f"+2135552000{index:02d}",
            )

            patient, _ = PatientProfile.objects.update_or_create(
                user=user,
                defaults={
                    "gender": blueprint["gender"],
                    "blood_group": blueprint["blood_group"],
                    "allergies": blueprint["allergies"],
                    "emergency_contact_name": f"Contact {index:02d}",
                    "emergency_contact_phone": f"+2136660000{index:02d}",
                    "address": f"Demo district block {index:02d}",
                    "is_account_deleted": False,
                    "account_deleted_at": None,
                    "deleted_by": None,
                },
            )
            patients.append(patient)

        return patients

    def _upsert_medical_records(self, patients):
        for patient in patients:
            MedicalRecord.objects.update_or_create(
                patient=patient,
                defaults={
                    "patient_full_name": f"{patient.user.first_name} {patient.user.last_name}".strip(),
                    "patient_date_of_birth": patient.dob,
                    "patient_gender": patient.gender,
                    "patient_phone": patient.user.phone_number,
                    "patient_address": patient.address,
                    "emergency_contact_name": patient.emergency_contact_name,
                    "emergency_contact_phone": patient.emergency_contact_phone,
                    "status": MedicalRecord.Status.ACTIVE,
                },
            )

    def _upsert_doctor_availability(self, doctors):
        for doctor in doctors:
            for weekday in range(0, 5):
                slot, _ = DoctorAvailabilitySlot.objects.get_or_create(
                    doctor=doctor,
                    weekday=weekday,
                    start_time=time(8, 0),
                    end_time=time(16, 0),
                )
                if not slot.is_active:
                    slot.is_active = True
                    slot.save(update_fields=["is_active"])

    def _upsert_appointments(self, doctors, patients):
        appointments = {}
        for blueprint in APPOINTMENT_BLUEPRINTS:
            marker = blueprint["marker"]
            patient = patients[blueprint["patient_index"]]
            doctor = doctors[blueprint["doctor_index"]]
            scheduled_at = self._build_slot_datetime(
                day_offset=blueprint["day_offset"],
                hour=blueprint["hour"],
            )

            existing = Appointment.objects.filter(notes__icontains=marker).first()
            defaults = {
                "patient": patient,
                "doctor": doctor,
                "scheduled_at": scheduled_at,
                "status": blueprint["status"],
                "urgency_level": blueprint["urgency"],
                "department": doctor.department,
                "reason": blueprint["reason"],
                "notes": f"[{marker}] Seeded demo appointment.",
                "last_staff_action_at": timezone.now() if blueprint["status"] != Appointment.Status.PENDING else None,
            }

            if existing:
                for key, value in defaults.items():
                    setattr(existing, key, value)
                existing.save()
                appointment = existing
            else:
                appointment = Appointment.objects.create(**defaults)

            appointments[marker] = appointment

        return appointments

    def _upsert_consultations(self, appointments_by_marker):
        consultation_blueprints = [
            {
                "marker": "DEMO_APPT_01",
                "diagnosis": "Viral syndrome with moderate dehydration",
                "anamnesis": "Symptoms started 4 days ago, no severe warning signs.",
                "treatment_plan": "Hydration protocol, rest, and symptomatic treatment for 5 days.",
                "vitals": {"temperature": "38.2", "heart_rate": "94"},
            },
            {
                "marker": "DEMO_APPT_02",
                "diagnosis": "Stage 1 hypertension with stress-related chest pain",
                "anamnesis": "Episodes occur under stress and physical effort.",
                "treatment_plan": "Lifestyle plan, BP monitoring, and cardiology follow-up in 2 weeks.",
                "vitals": {"bp": "145/95", "heart_rate": "88"},
            },
            {
                "marker": "DEMO_APPT_03",
                "diagnosis": "Post-infectious bronchial hyperreactivity",
                "anamnesis": "Dry cough persisted after resolved upper respiratory infection.",
                "treatment_plan": "Inhaled therapy trial and symptom tracking over 10 days.",
                "vitals": {"spo2": "97", "respiratory_rate": "20"},
            },
        ]

        consultations = []
        for blueprint in consultation_blueprints:
            appointment = appointments_by_marker[blueprint["marker"]]
            medical_record = appointment.patient.medical_record

            consultation, _ = Consultation.objects.update_or_create(
                appointment=appointment,
                defaults={
                    "medical_record": medical_record,
                    "doctor": appointment.doctor,
                    "diagnosis": blueprint["diagnosis"],
                    "anamnesis": blueprint["anamnesis"],
                    "treatment_plan": blueprint["treatment_plan"],
                    "vitals": blueprint["vitals"],
                },
            )
            consultations.append(consultation)

            medical_record.diagnostic_summary = blueprint["diagnosis"]
            medical_record.treatment_management = blueprint["treatment_plan"]
            medical_record.status = MedicalRecord.Status.ACTIVE
            medical_record.save(update_fields=["diagnostic_summary", "treatment_management", "status", "updated_at"])

        return consultations

    def _upsert_prescriptions(self, consultations):
        if len(consultations) < 2:
            return

        prescription_specs = [
            {
                "consultation": consultations[0],
                "notes": "Hydration and antipyretic protocol for 5 days.",
                "items": [
                    {
                        "medication": "Paracetamol",
                        "dosage": "500mg",
                        "frequency": "Every 8h",
                        "duration": "5 days",
                        "instructions": "After meals if possible.",
                    },
                    {
                        "medication": "Oral rehydration salts",
                        "dosage": "1 sachet",
                        "frequency": "Twice daily",
                        "duration": "3 days",
                        "instructions": "Dilute in clean water.",
                    },
                ],
            },
            {
                "consultation": consultations[1],
                "notes": "Cardiovascular risk reduction plan.",
                "items": [
                    {
                        "medication": "Amlodipine",
                        "dosage": "5mg",
                        "frequency": "Once daily",
                        "duration": "30 days",
                        "instructions": "Take at the same hour every day.",
                    }
                ],
            },
        ]

        for spec in prescription_specs:
            consultation = spec["consultation"]
            prescription, _ = Prescription.objects.update_or_create(
                consultation=consultation,
                defaults={
                    "doctor": consultation.doctor,
                    "patient": consultation.medical_record.patient,
                    "notes": spec["notes"],
                },
            )

            prescription.items.all().delete()
            for item in spec["items"]:
                PrescriptionItem.objects.create(prescription=prescription, **item)

    def _upsert_follow_up(self, consultations):
        if len(consultations) < 3:
            return

        follow_up_specs = [
            {
                "consultation": consultations[1],
                "day_offset": 6,
                "status": FollowUp.Status.SCHEDULED,
                "notes": "[DEMO_FOLLOWUP_01] Blood pressure reassessment and treatment adherence.",
            },
            {
                "consultation": consultations[2],
                "day_offset": 8,
                "status": FollowUp.Status.SCHEDULED,
                "notes": "[DEMO_FOLLOWUP_02] Respiratory symptom progression review.",
            },
        ]

        for spec in follow_up_specs:
            consultation = spec["consultation"]
            scheduled_at = self._build_slot_datetime(day_offset=spec["day_offset"], hour=10)
            follow_up, _ = FollowUp.objects.update_or_create(
                consultation=consultation,
                defaults={
                    "patient": consultation.medical_record.patient,
                    "doctor": consultation.doctor,
                    "scheduled_at": scheduled_at,
                    "status": spec["status"],
                    "notes": spec["notes"],
                },
            )

            FollowUpAlert.objects.update_or_create(
                follow_up=follow_up,
                alert_type=FollowUpAlert.Type.EMAIL,
                defaults={
                    "scheduled_at": scheduled_at - timedelta(days=1),
                    "status": FollowUpAlert.Status.PENDING,
                    "message": "Automated reminder: upcoming follow-up consultation.",
                },
            )

    def _upsert_document_requests(self, consultations):
        if len(consultations) < 3:
            return

        consultation = consultations[2]
        due_date = (timezone.localtime(timezone.now()) + timedelta(days=7)).date()

        MedicalDocumentRequest.objects.update_or_create(
            medical_record=consultation.medical_record,
            doctor=consultation.doctor,
            title="Respiratory control panel",
            defaults={
                "request_type": MedicalDocumentRequest.RequestType.ANALYSIS,
                "description": "Upload CBC and CRP results before next follow-up.",
                "requested_items": ["CBC", "CRP"],
                "due_date": due_date,
                "status": MedicalDocumentRequest.Status.PENDING,
            },
        )

    def _upsert_notifications(self, admin_user, doctors, patients, appointments_by_marker):
        for appointment in appointments_by_marker.values():
            self._upsert_notification(
                recipient=appointment.patient.user,
                notification_type=Notification.Type.APPOINTMENT,
                title="Appointment scheduled",
                message=(
                    f"Appointment with Dr. {appointment.doctor.user.last_name} on "
                    f"{timezone.localtime(appointment.scheduled_at).strftime('%Y-%m-%d %H:%M')} "
                    f"is currently {appointment.status}."
                ),
            )

        for doctor in doctors:
            self._upsert_notification(
                recipient=doctor.user,
                notification_type=Notification.Type.SYSTEM,
                title="Demo workload available",
                message="Demo patients and appointments are available for workflow testing.",
            )

        self._upsert_notification(
            recipient=admin_user,
            notification_type=Notification.Type.SYSTEM,
            title="Demo platform initialized",
            message=(
                "The demo scenario includes 5 doctors, 10 patients, and 10 appointments with "
                "history, prescriptions, follow-up, and notifications."
            ),
        )

        for patient in patients[:2]:
            self._upsert_notification(
                recipient=patient.user,
                notification_type=Notification.Type.FOLLOW_UP,
                title="Follow-up reminder",
                message="Check your patient dashboard for next follow-up actions.",
            )

    def _upsert_leave_request(self, admin_user, doctor):
        start_date = (timezone.localtime(timezone.now()) + timedelta(days=10)).date()
        end_date = start_date + timedelta(days=2)

        DoctorLeave.objects.update_or_create(
            doctor=doctor,
            start_date=start_date,
            end_date=end_date,
            defaults={
                "reason": "Annual leave request for demo validation.",
                "status": DoctorLeave.Status.PENDING,
                "is_active": False,
                "created_by": admin_user,
                "reviewed_by": None,
                "reviewed_at": None,
                "review_note": "",
            },
        )

    def _upsert_chatbot_conversations(self, patients):
        conversation_specs = [
            {
                "marker": "DEMO_CHAT_01",
                "patient_index": 0,
                "title": "[DEMO_CHAT_01] Flu-like symptoms",
                "messages": [
                    "I have fever, sore throat, and fatigue since yesterday.",
                    "Symptoms are moderate and getting slightly worse.",
                ],
            },
            {
                "marker": "DEMO_CHAT_02",
                "patient_index": 1,
                "title": "[DEMO_CHAT_02] Cardio concern",
                "messages": [
                    "I feel chest discomfort when climbing stairs.",
                    "No severe pain at rest, but I feel pressure and shortness of breath.",
                ],
            },
            {
                "marker": "DEMO_CHAT_03",
                "patient_index": 2,
                "title": "[DEMO_CHAT_03] Respiratory follow-up",
                "messages": [
                    "Persistent cough for more than one week.",
                    "I also have mild wheezing at night.",
                ],
            },
        ]

        created_count = 0
        for spec in conversation_specs:
            patient = patients[spec["patient_index"]]
            primary_message = spec["messages"][0]
            assistant_payload = build_health_chat_response(
                primary_message,
                wants_appointment=True,
                require_auth_for_booking=False,
            )

            session, created = ChatbotSession.objects.update_or_create(
                patient=patient,
                title=spec["title"],
                defaults={
                    "booked_appointment": None,
                    "awaiting_appointment_confirmation": False,
                    "latest_analysis": assistant_payload.get("analysis") or {},
                    "is_closed": False,
                },
            )
            if created:
                created_count += 1

            session.messages.all().delete()

            for raw_message in spec["messages"]:
                ChatbotMessage.objects.create(
                    session=session,
                    sender=ChatbotMessage.Sender.PATIENT,
                    content=raw_message,
                )

                bot_payload = build_health_chat_response(
                    raw_message,
                    wants_appointment=True,
                    require_auth_for_booking=False,
                )
                bot_metadata = {
                    "response_type": bot_payload.get("response_type"),
                }
                if bot_payload.get("analysis"):
                    bot_metadata["analysis"] = bot_payload["analysis"]

                ChatbotMessage.objects.create(
                    session=session,
                    sender=ChatbotMessage.Sender.BOT,
                    content=bot_payload.get("reply") or "No assistant response generated.",
                    metadata=bot_metadata,
                )

        return len(conversation_specs)

    def _upsert_notification(self, recipient, notification_type, title, message):
        Notification.objects.get_or_create(
            recipient=recipient,
            notification_type=notification_type,
            title=title,
            message=message,
            defaults={"is_read": False},
        )

    def _upsert_user(
        self,
        *,
        email,
        username,
        role,
        password,
        first_name,
        last_name,
        phone_number,
        is_staff=False,
        is_superuser=False,
    ):
        user = CustomUser.objects.filter(email=email).first()
        if not user:
            user = CustomUser.objects.create_user(
                email=email,
                username=username,
                role=role,
                first_name=first_name,
                last_name=last_name,
                phone_number=phone_number,
                password=password,
                is_active=True,
                is_staff=is_staff,
                is_superuser=is_superuser,
                is_verified=True,
            )
            return user

        user.username = username
        user.role = role
        user.first_name = first_name
        user.last_name = last_name
        user.phone_number = phone_number
        user.is_active = True
        user.is_staff = is_staff
        user.is_superuser = is_superuser
        user.is_verified = True
        user.set_password(password)
        user.save()
        return user

    def _build_slot_datetime(self, day_offset, hour, minute=0):
        current_tz = timezone.get_current_timezone()
        base = timezone.localtime(timezone.now(), current_tz)
        target = (base + timedelta(days=day_offset)).replace(hour=hour, minute=minute, second=0, microsecond=0)

        if target.weekday() == 6:
            target = target + timedelta(days=1)

        return target

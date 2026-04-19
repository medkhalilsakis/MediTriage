import uuid
from datetime import timedelta

from django.db import transaction
from django.db.models import Avg, Count, Q
from django.db.models.functions import ExtractWeekDay, TruncDate, TruncMonth, TruncWeek
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenRefreshView

from appointments.models import Appointment
from medical_records.models import Consultation, MedicalRecord
from prescriptions.models import Prescription
from patients.models import PatientProfile
from doctors.models import DoctorProfile

from .models import CustomUser
from .permissions import IsAdmin
from .serializers import AccountMeSerializer, AuthResponseSerializer, LoginSerializer, RegisterSerializer


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(AuthResponseSerializer.build(user, request=request), status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        return Response(AuthResponseSerializer.build(serializer.validated_data['user'], request=request))


class AccountMeView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = AccountMeSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_object(self):
        return self.request.user

    def _create_deleted_user_placeholder(self):
        identity_suffix = uuid.uuid4().hex[:12]
        username = f'deleted-user-{identity_suffix}'
        placeholder = CustomUser.objects.create_user(
            email=f'{username}@deleted.local',
            username=username,
            password=None,
            first_name='Deleted',
            last_name='User',
            role=CustomUser.Role.PATIENT,
            is_active=False,
            is_verified=False,
            phone_number='',
        )
        placeholder.set_unusable_password()
        placeholder.save(update_fields=['password'])
        return placeholder

    def _anonymize_patient_history_and_delete_account(self, user):
        now = timezone.now()
        patient_profile = PatientProfile.objects.select_related('user').filter(user=user).first()

        if not patient_profile:
            if user.profile_image:
                user.profile_image.delete(save=False)
            user.delete()
            return {
                'removed_future_appointments': 0,
                'medical_record_archived': False,
            }

        future_appointments = Appointment.objects.filter(
            patient=patient_profile,
            scheduled_at__gt=now,
        )
        removed_future_appointments = future_appointments.count()
        future_appointments.delete()

        medical_record_archived = False
        medical_record = MedicalRecord.objects.filter(patient=patient_profile).first()
        if medical_record:
            update_fields = [
                'patient_full_name',
                'patient_date_of_birth',
                'patient_gender',
                'patient_phone',
                'patient_address',
                'emergency_contact_name',
                'emergency_contact_phone',
                'social_security_number',
                'updated_at',
            ]
            medical_record.patient_full_name = PatientProfile.DELETED_USER_LABEL
            medical_record.patient_date_of_birth = None
            medical_record.patient_gender = ''
            medical_record.patient_phone = ''
            medical_record.patient_address = ''
            medical_record.emergency_contact_name = ''
            medical_record.emergency_contact_phone = ''
            medical_record.social_security_number = ''

            if medical_record.status != MedicalRecord.Status.ARCHIVED:
                medical_record.status = MedicalRecord.Status.ARCHIVED
                if not medical_record.closed_at:
                    medical_record.closed_at = now
                medical_record.archived_at = now
                medical_record.archived_by = None
                update_fields.extend(['status', 'closed_at', 'archived_at', 'archived_by'])
                medical_record_archived = True

            medical_record.save(update_fields=update_fields)

        placeholder_user = self._create_deleted_user_placeholder()
        patient_profile.user = placeholder_user
        patient_profile.dob = None
        patient_profile.gender = ''
        patient_profile.blood_group = ''
        patient_profile.allergies = ''
        patient_profile.emergency_contact_name = ''
        patient_profile.emergency_contact_phone = ''
        patient_profile.address = ''
        patient_profile.is_account_deleted = True
        patient_profile.account_deleted_at = now
        patient_profile.deleted_by = None
        patient_profile.save(
            update_fields=[
                'user',
                'dob',
                'gender',
                'blood_group',
                'allergies',
                'emergency_contact_name',
                'emergency_contact_phone',
                'address',
                'is_account_deleted',
                'account_deleted_at',
                'deleted_by',
                'updated_at',
            ]
        )

        if user.profile_image:
            user.profile_image.delete(save=False)
        user.delete()

        return {
            'removed_future_appointments': removed_future_appointments,
            'medical_record_archived': medical_record_archived,
        }

    def destroy(self, request, *args, **kwargs):
        user = self.get_object()

        if user.role != CustomUser.Role.PATIENT:
            return super().destroy(request, *args, **kwargs)

        with transaction.atomic():
            summary = self._anonymize_patient_history_and_delete_account(user)

        return Response(
            {
                'detail': 'Account deleted. Medical history is preserved under deleted user.',
                'history_owner_label': PatientProfile.DELETED_USER_LABEL,
                **summary,
            },
            status=status.HTTP_200_OK,
        )


class AdminStatsView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        now = timezone.now()
        start_last_30_days = now - timedelta(days=30)
        start_last_9_months = now - timedelta(days=270)

        consultations_by_week = (
            Consultation.objects.annotate(week=TruncWeek('created_at'))
            .values('week')
            .annotate(count=Count('id'))
            .order_by('week')
        )
        urgency_split = (
            Appointment.objects.values('urgency_level')
            .annotate(count=Count('id'))
            .order_by('urgency_level')
        )

        users_by_role = (
            CustomUser.objects.values('role')
            .annotate(count=Count('id'))
            .order_by('role')
        )

        appointments_by_status = (
            Appointment.objects.values('status')
            .annotate(count=Count('id'))
            .order_by('status')
        )

        appointments_by_department = (
            Appointment.objects.values('department')
            .annotate(count=Count('id'))
            .order_by('department')
        )

        appointments_by_month = (
            Appointment.objects.filter(created_at__gte=start_last_9_months)
            .annotate(month=TruncMonth('created_at'))
            .values('month')
            .annotate(count=Count('id'))
            .order_by('month')
        )

        consultations_by_month = (
            Consultation.objects.filter(created_at__gte=start_last_9_months)
            .annotate(month=TruncMonth('created_at'))
            .values('month')
            .annotate(count=Count('id'))
            .order_by('month')
        )

        activity_last_30_days = (
            Appointment.objects.filter(created_at__gte=start_last_30_days)
            .annotate(day=TruncDate('created_at'))
            .values('day')
            .annotate(
                appointments=Count('id'),
                completed=Count('id', filter=Q(status=Appointment.Status.COMPLETED)),
                cancelled=Count('id', filter=Q(status=Appointment.Status.CANCELLED)),
            )
            .order_by('day')
        )

        appointments_by_weekday = (
            Appointment.objects.annotate(weekday=ExtractWeekDay('scheduled_at'))
            .values('weekday')
            .annotate(count=Count('id'))
            .order_by('weekday')
        )

        top_doctors_by_load = (
            Appointment.objects.values('doctor', 'doctor__user__email', 'doctor__department')
            .annotate(
                total=Count('id'),
                completed=Count('id', filter=Q(status=Appointment.Status.COMPLETED)),
                pending=Count('id', filter=Q(status=Appointment.Status.PENDING)),
                confirmed=Count('id', filter=Q(status=Appointment.Status.CONFIRMED)),
                cancelled=Count('id', filter=Q(status=Appointment.Status.CANCELLED)),
                no_show=Count('id', filter=Q(status=Appointment.Status.NO_SHOW)),
            )
            .order_by('-total', 'doctor__user__email')[:10]
        )

        per_doctor_load = (
            Appointment.objects.values('doctor')
            .annotate(total=Count('id'))
        )
        avg_appointments_per_doctor = per_doctor_load.aggregate(avg=Avg('total')).get('avg') or 0

        appointments_total = Appointment.objects.count()
        no_show_count = Appointment.objects.filter(status=Appointment.Status.NO_SHOW).count()
        cancelled_count = Appointment.objects.filter(status=Appointment.Status.CANCELLED).count()
        completed_count = Appointment.objects.filter(status=Appointment.Status.COMPLETED).count()
        confirmed_or_pending_count = Appointment.objects.filter(
            status__in=[Appointment.Status.CONFIRMED, Appointment.Status.PENDING]
        ).count()

        active_patients_last_30_days = PatientProfile.objects.filter(
            appointments__created_at__gte=start_last_30_days
        ).distinct().count()

        no_show_rate = (no_show_count / appointments_total * 100.0) if appointments_total else 0.0
        cancellation_rate = (cancelled_count / appointments_total * 100.0) if appointments_total else 0.0
        completion_rate = (completed_count / appointments_total * 100.0) if appointments_total else 0.0

        data = {
            'users_total': request.user.__class__.objects.count(),
            'patients_total': PatientProfile.objects.count(),
            'doctors_total': DoctorProfile.objects.count(),
            'appointments_total': appointments_total,
            'consultations_total': Consultation.objects.count(),
            'prescriptions_total': Prescription.objects.count(),
            'consultations_by_week': list(consultations_by_week),
            'urgency_split': list(urgency_split),
            'users_by_role': list(users_by_role),
            'appointments_by_status': list(appointments_by_status),
            'appointments_by_department': list(appointments_by_department),
            'appointments_by_month': list(appointments_by_month),
            'consultations_by_month': list(consultations_by_month),
            'activity_last_30_days': list(activity_last_30_days),
            'appointments_by_weekday': list(appointments_by_weekday),
            'top_doctors_by_load': list(top_doctors_by_load),
            'active_patients_last_30_days': active_patients_last_30_days,
            'average_appointments_per_doctor': round(float(avg_appointments_per_doctor), 2),
            'open_appointments_count': confirmed_or_pending_count,
            'completion_rate': round(completion_rate, 2),
            'no_show_rate': round(no_show_rate, 2),
            'cancellation_rate': round(cancellation_rate, 2),
            'generated_at': now,
        }
        return Response(data)


class JWTRefreshView(TokenRefreshView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

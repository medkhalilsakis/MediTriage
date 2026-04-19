from django.db import transaction
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from authentication.permissions import IsAdmin
from appointments.models import Appointment
from medical_records.models import MedicalRecord

from .models import PatientProfile
from .serializers import PatientProfileSerializer


class PatientProfileViewSet(viewsets.ModelViewSet):
    serializer_class = PatientProfileSerializer
    queryset = PatientProfile.objects.select_related('user').all()
    filterset_fields = ['gender', 'blood_group']
    search_fields = ['user__email', 'user__first_name', 'user__last_name', 'allergies']
    ordering_fields = ['created_at', 'updated_at']

    def get_permissions(self):
        if self.action in ['destroy', 'delete_account']:
            permission_classes = [permissions.IsAuthenticated, IsAdmin]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        user = self.request.user
        qs = self.queryset
        if user.role == 'patient':
            return qs.filter(user=user, is_account_deleted=False)
        if user.role == 'admin':
            return qs
        return qs.filter(is_account_deleted=False, user__is_active=True)

    def _archive_patient_account(self, patient_profile, actor):
        now = timezone.now()

        future_appointments = Appointment.objects.filter(
            patient=patient_profile,
            scheduled_at__gt=now,
        )
        removed_future_appointments = future_appointments.count()
        future_appointments.delete()

        archived_record = False
        medical_record = MedicalRecord.objects.filter(patient=patient_profile).first()
        if medical_record and medical_record.status != MedicalRecord.Status.ARCHIVED:
            medical_record.status = MedicalRecord.Status.ARCHIVED
            if not medical_record.closed_at:
                medical_record.closed_at = now
            medical_record.archived_at = now
            medical_record.archived_by = actor
            medical_record.save(update_fields=['status', 'closed_at', 'archived_at', 'archived_by', 'updated_at'])
            archived_record = True

        user = patient_profile.user
        if user.is_active:
            user.is_active = False
            user.save(update_fields=['is_active'])

        patient_profile.is_account_deleted = True
        patient_profile.account_deleted_at = now
        patient_profile.deleted_by = actor
        patient_profile.save(update_fields=['is_account_deleted', 'account_deleted_at', 'deleted_by', 'updated_at'])

        return {
            'removed_future_appointments': removed_future_appointments,
            'medical_record_archived': archived_record,
        }

    @action(detail=True, methods=['post'], url_path='delete-account')
    def delete_account(self, request, pk=None):
        if request.user.role != 'admin':
            raise PermissionDenied('Only admin can delete patient accounts.')

        patient_profile = self.get_object()
        with transaction.atomic():
            summary = self._archive_patient_account(patient_profile, request.user)

        return Response(
            {
                'detail': 'Patient account archived. Future appointments were removed and historical data preserved.',
                **summary,
            },
            status=status.HTTP_200_OK,
        )

    def destroy(self, request, *args, **kwargs):
        if request.user.role != 'admin':
            raise PermissionDenied('Only admin can delete patient accounts.')

        patient_profile = self.get_object()
        with transaction.atomic():
            summary = self._archive_patient_account(patient_profile, request.user)

        return Response(
            {
                'detail': 'Patient account archived. Future appointments were removed and historical data preserved.',
                **summary,
            },
            status=status.HTTP_200_OK,
        )

    def perform_create(self, serializer):
        if self.request.user.role not in ['admin', 'doctor']:
            raise PermissionDenied('Only doctor or admin can create patient profiles.')
        serializer.save()

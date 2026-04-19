from datetime import date

from django.db import transaction
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from doctors.models import DoctorProfile
from medical_records.operations import ensure_doctor_not_blocked_now

from .models import Appointment, AppointmentAdvanceOffer
from .scheduling import (
    DEFAULT_END_TIME,
    DEFAULT_START_TIME,
    MAX_PATIENTS_PER_HOUR,
    SLOT_DURATION_MINUTES,
    assign_doctor_and_slot,
    is_doctor_available_for_slot,
    normalize_slot_datetime,
)
from .serializers import AppointmentAdvanceOfferSerializer, AppointmentSerializer
from .workflows import (
    auto_postpone_unhandled_appointments,
    close_pending_offers_for_appointment,
    expire_pending_advance_offers,
    respond_to_advance_offer,
    trigger_waitlist_for_freed_slot,
)


class AppointmentViewSet(viewsets.ModelViewSet):
    serializer_class = AppointmentSerializer
    queryset = Appointment.objects.select_related('patient__user', 'doctor__user').all()
    filterset_fields = ['patient', 'doctor', 'status', 'urgency_level', 'department']
    search_fields = ['patient__user__email', 'doctor__user__email', 'department', 'reason', 'notes']
    ordering_fields = ['scheduled_at', 'created_at', 'updated_at']

    def get_permissions(self):
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        auto_postpone_unhandled_appointments()
        expire_pending_advance_offers()
        user = self.request.user
        qs = self.queryset
        if user.role == 'patient':
            return qs.filter(patient__user=user)
        if user.role == 'doctor':
            return qs.filter(doctor__user=user)
        return qs

    @action(detail=False, methods=['get'], url_path='today')
    def today(self, request):
        user = request.user
        if user.role != 'doctor':
            return Response({'detail': 'Only doctors can access today appointments.'}, status=status.HTTP_403_FORBIDDEN)

        expire_pending_advance_offers()
        raw_date = request.query_params.get('date')
        if raw_date:
            try:
                target_date = date.fromisoformat(raw_date)
            except ValueError as exc:
                raise ValidationError({'date': 'Invalid date format. Use YYYY-MM-DD.'}) from exc
        else:
            target_date = timezone.localdate()

        items = self.get_queryset().filter(scheduled_at__date=target_date).order_by('scheduled_at', 'id')
        page = self.paginate_queryset(items)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(items, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='accept')
    def accept(self, request, pk=None):
        appointment = self.get_object()
        self._ensure_staff_can_manage_appointment(appointment, request.user)

        if request.user.role == 'doctor':
            ensure_doctor_not_blocked_now(appointment.doctor, action_label='accept appointments')

        appointment.status = Appointment.Status.CONFIRMED
        appointment.last_staff_action_at = timezone.now()
        appointment.notes = self._append_action_note(
            appointment.notes,
            f"Appointment accepted by {request.user.role} {request.user.email}.",
        )
        appointment.save(update_fields=['status', 'last_staff_action_at', 'notes', 'updated_at'])
        return Response(self.get_serializer(appointment).data)

    @action(detail=True, methods=['post'], url_path='complete')
    def complete(self, request, pk=None):
        appointment = self.get_object()
        self._ensure_staff_can_manage_appointment(appointment, request.user)

        if request.user.role == 'doctor':
            ensure_doctor_not_blocked_now(appointment.doctor, action_label='complete appointments')

        if appointment.status in [Appointment.Status.CANCELLED, Appointment.Status.NO_SHOW]:
            raise ValidationError({'detail': 'Cancelled or no-show appointments cannot be completed.'})

        appointment.status = Appointment.Status.COMPLETED
        appointment.last_staff_action_at = timezone.now()
        appointment.notes = self._append_action_note(
            appointment.notes,
            f"Appointment marked as completed by {request.user.role} {request.user.email}.",
        )
        appointment.save(update_fields=['status', 'last_staff_action_at', 'notes', 'updated_at'])
        return Response(self.get_serializer(appointment).data)

    @action(detail=True, methods=['post'], url_path='delay')
    def delay(self, request, pk=None):
        appointment = self.get_object()
        user = request.user

        if user.role in ['doctor', 'admin']:
            if user.role == 'doctor' and appointment.doctor.user_id != user.id:
                raise PermissionDenied('Doctors can only delay their own appointments.')
        elif user.role == 'patient':
            if appointment.patient.user_id != user.id:
                raise PermissionDenied('Patients can only delay their own appointments.')
        else:
            raise PermissionDenied('You do not have permission to delay this appointment.')

        new_slot = self._extract_validated_slot(appointment, request.data.get('scheduled_at'))
        if not is_doctor_available_for_slot(
            doctor=appointment.doctor,
            slot_datetime=new_slot,
            exclude_appointment_id=appointment.id,
        ):
            raise ValidationError({'scheduled_at': 'Selected slot is not available for this doctor.'})

        old_slot = appointment.scheduled_at
        close_pending_offers_for_appointment(appointment)

        appointment.scheduled_at = new_slot
        appointment.status = Appointment.Status.CONFIRMED
        if user.role in ['doctor', 'admin']:
            appointment.last_staff_action_at = timezone.now()
        appointment.notes = self._append_action_note(
            appointment.notes,
            f"Appointment delayed by {user.role} {user.email} to {timezone.localtime(new_slot).strftime('%Y-%m-%d %H:%M')}.",
        )
        update_fields = ['scheduled_at', 'status', 'notes', 'updated_at']
        if user.role in ['doctor', 'admin']:
            update_fields.append('last_staff_action_at')
        appointment.save(update_fields=update_fields)

        if old_slot != new_slot:
            trigger_waitlist_for_freed_slot(doctor=appointment.doctor, freed_slot=old_slot, actor=user)

        return Response(self.get_serializer(appointment).data)

    @action(detail=True, methods=['post'], url_path='reassign')
    def reassign(self, request, pk=None):
        appointment = self.get_object()
        user = request.user
        self._ensure_staff_can_manage_appointment(appointment, user)

        doctor_id = request.data.get('doctor') or request.data.get('doctor_id')
        if not doctor_id:
            raise ValidationError({'doctor': 'Target doctor id is required.'})

        try:
            target_doctor = DoctorProfile.objects.select_related('user').get(pk=doctor_id)
        except DoctorProfile.DoesNotExist as exc:
            raise ValidationError({'doctor': 'Target doctor does not exist.'}) from exc

        if request.data.get('scheduled_at'):
            target_slot = self._extract_validated_slot(appointment, request.data.get('scheduled_at'))
        else:
            target_slot = appointment.scheduled_at

        if not is_doctor_available_for_slot(
            doctor=target_doctor,
            slot_datetime=target_slot,
            exclude_appointment_id=appointment.id,
        ):
            raise ValidationError({'scheduled_at': 'Selected slot is not available for the target doctor.'})

        old_slot = appointment.scheduled_at
        old_doctor = appointment.doctor
        close_pending_offers_for_appointment(appointment)

        appointment.doctor = target_doctor
        appointment.department = target_doctor.department
        appointment.scheduled_at = target_slot
        appointment.status = Appointment.Status.CONFIRMED
        appointment.last_staff_action_at = timezone.now()
        appointment.notes = self._append_action_note(
            appointment.notes,
            (
                f"Appointment reassigned by {user.role} {user.email} to Dr. {target_doctor.user.email} "
                f"for {timezone.localtime(target_slot).strftime('%Y-%m-%d %H:%M')}."
            ),
        )
        appointment.save(
            update_fields=['doctor', 'department', 'scheduled_at', 'status', 'last_staff_action_at', 'notes', 'updated_at']
        )

        if old_doctor.id != target_doctor.id or old_slot != target_slot:
            trigger_waitlist_for_freed_slot(doctor=old_doctor, freed_slot=old_slot, actor=user)

        return Response(self.get_serializer(appointment).data)

    @action(detail=True, methods=['post'], url_path='request-reschedule')
    def request_reschedule(self, request, pk=None):
        appointment = self.get_object()
        user = request.user
        if user.role != 'patient' or appointment.patient.user_id != user.id:
            raise PermissionDenied('Only the appointment patient can request a reschedule.')

        if appointment.status in [Appointment.Status.CANCELLED, Appointment.Status.COMPLETED, Appointment.Status.NO_SHOW]:
            raise ValidationError({'detail': 'This appointment cannot be rescheduled.'})

        new_slot = self._extract_validated_slot(appointment, request.data.get('scheduled_at'))
        if not is_doctor_available_for_slot(
            doctor=appointment.doctor,
            slot_datetime=new_slot,
            exclude_appointment_id=appointment.id,
        ):
            raise ValidationError({'scheduled_at': 'Selected slot is not available for this doctor.'})

        old_slot = appointment.scheduled_at
        close_pending_offers_for_appointment(appointment)

        appointment.scheduled_at = new_slot
        appointment.status = Appointment.Status.CONFIRMED
        appointment.notes = self._append_action_note(
            appointment.notes,
            f"Patient requested reschedule to {timezone.localtime(new_slot).strftime('%Y-%m-%d %H:%M')}.",
        )
        appointment.save(update_fields=['scheduled_at', 'status', 'notes', 'updated_at'])

        if old_slot != new_slot:
            trigger_waitlist_for_freed_slot(doctor=appointment.doctor, freed_slot=old_slot, actor=user)

        return Response(self.get_serializer(appointment).data)

    def perform_create(self, serializer):
        user = self.request.user
        expire_pending_advance_offers()

        if user.role == 'patient':
            patient_profile = getattr(user, 'patient_profile', None)
            if not patient_profile:
                raise ValidationError({'patient': 'Patient profile is missing for this account.'})

            requested_department = (
                serializer.validated_data.get('department') or Appointment.Department.GENERAL_MEDICINE
            )

            with transaction.atomic():
                doctor, scheduled_at, effective_department = assign_doctor_and_slot(
                    requested_department=requested_department,
                    now=timezone.now(),
                )

                if not doctor or not scheduled_at:
                    raise ValidationError(
                        {'detail': 'No doctor is currently available for automated scheduling.'}
                    )

                serializer.save(
                    patient=patient_profile,
                    doctor=doctor,
                    scheduled_at=scheduled_at,
                    department=effective_department,
                    status=Appointment.Status.CONFIRMED,
                )
            return

        if user.role == 'doctor':
            doctor_profile = getattr(user, 'doctor_profile', None)
            if not doctor_profile:
                raise ValidationError({'doctor': 'Doctor profile is missing for this account.'})

            patient = serializer.validated_data.get('patient')
            scheduled_at = serializer.validated_data.get('scheduled_at')
            if not patient:
                raise ValidationError({'patient': 'This field is required.'})
            if not scheduled_at:
                raise ValidationError({'scheduled_at': 'This field is required.'})
            scheduled_at = self._ensure_slot_alignment(scheduled_at)
            if not is_doctor_available_for_slot(doctor=doctor_profile, slot_datetime=scheduled_at):
                raise ValidationError({'scheduled_at': 'Selected slot is not available for this doctor.'})

            serializer.save(
                doctor=doctor_profile,
                scheduled_at=scheduled_at,
                department=serializer.validated_data.get('department') or doctor_profile.department,
                status=Appointment.Status.CONFIRMED,
                last_staff_action_at=timezone.now(),
            )
            return

        doctor = serializer.validated_data.get('doctor')
        patient = serializer.validated_data.get('patient')
        scheduled_at = serializer.validated_data.get('scheduled_at')
        if not patient:
            raise ValidationError({'patient': 'This field is required.'})
        if not doctor:
            raise ValidationError({'doctor': 'This field is required.'})
        if not scheduled_at:
            raise ValidationError({'scheduled_at': 'This field is required.'})
        scheduled_at = self._ensure_slot_alignment(scheduled_at)
        if not is_doctor_available_for_slot(doctor=doctor, slot_datetime=scheduled_at):
            raise ValidationError({'scheduled_at': 'Selected slot is not available for this doctor.'})

        serializer.save(
            scheduled_at=scheduled_at,
            department=serializer.validated_data.get('department') or doctor.department,
            status=Appointment.Status.CONFIRMED,
            last_staff_action_at=timezone.now(),
        )

    def perform_update(self, serializer):
        user = self.request.user
        appointment = serializer.instance
        old_slot = appointment.scheduled_at
        old_doctor = appointment.doctor
        old_status = appointment.status

        if user.role == 'patient':
            immutable_fields = {'patient', 'doctor', 'scheduled_at', 'urgency_level', 'department', 'reason'}
            requested_fields = set(serializer.validated_data.keys())
            blocked_fields = requested_fields.intersection(immutable_fields)
            if blocked_fields:
                raise ValidationError(
                    {
                        'detail': (
                            'Patients cannot modify doctor assignment, department, urgency, reason, or schedule '
                            'after automatic booking. Use request-reschedule endpoint for date changes.'
                        )
                    }
                )

            if (
                'status' in serializer.validated_data
                and serializer.validated_data['status'] != Appointment.Status.CANCELLED
            ):
                raise ValidationError({'status': 'Patients can only cancel appointments.'})

        if user.role == 'doctor' and appointment.doctor.user_id != user.id:
            raise PermissionDenied('Doctors can only update their own appointments.')

        requested_doctor = serializer.validated_data.get('doctor', appointment.doctor)
        requested_slot = serializer.validated_data.get('scheduled_at', appointment.scheduled_at)

        if 'scheduled_at' in serializer.validated_data and requested_slot <= timezone.now():
            raise ValidationError({'scheduled_at': 'Scheduled date must be in the future.'})

        if 'scheduled_at' in serializer.validated_data:
            requested_slot = self._ensure_slot_alignment(requested_slot)
            serializer.validated_data['scheduled_at'] = requested_slot

        if 'doctor' in serializer.validated_data or 'scheduled_at' in serializer.validated_data:
            if not is_doctor_available_for_slot(
                doctor=requested_doctor,
                slot_datetime=requested_slot,
                exclude_appointment_id=appointment.id,
            ):
                raise ValidationError({'scheduled_at': 'Selected slot is not available for the selected doctor.'})

        updated = serializer.save(
            department=serializer.validated_data.get('department') or requested_doctor.department,
            last_staff_action_at=timezone.now() if user.role in ['doctor', 'admin'] else appointment.last_staff_action_at,
        )

        schedule_or_doctor_changed = old_doctor.id != updated.doctor.id or old_slot != updated.scheduled_at
        if schedule_or_doctor_changed:
            close_pending_offers_for_appointment(updated)
            trigger_waitlist_for_freed_slot(doctor=old_doctor, freed_slot=old_slot, actor=user)

        became_cancelled = old_status != Appointment.Status.CANCELLED and updated.status == Appointment.Status.CANCELLED
        if became_cancelled:
            close_pending_offers_for_appointment(updated)
            trigger_waitlist_for_freed_slot(doctor=old_doctor, freed_slot=old_slot, actor=user)

    def _extract_validated_slot(self, appointment, raw_value):
        if raw_value in [None, '']:
            raise ValidationError({'scheduled_at': 'This field is required.'})

        validation_serializer = self.get_serializer(
            appointment,
            data={'scheduled_at': raw_value},
            partial=True,
        )
        validation_serializer.is_valid(raise_exception=True)
        new_slot = validation_serializer.validated_data.get('scheduled_at')
        if not new_slot:
            raise ValidationError({'scheduled_at': 'Invalid scheduled date.'})
        if new_slot <= timezone.now():
            raise ValidationError({'scheduled_at': 'Scheduled date must be in the future.'})

        return self._ensure_slot_alignment(new_slot)

    def _ensure_slot_alignment(self, slot_datetime):
        normalized_slot = normalize_slot_datetime(slot_datetime)
        local_slot = timezone.localtime(slot_datetime).replace(second=0, microsecond=0)
        if normalized_slot != local_slot:
            raise ValidationError(
                {
                    'scheduled_at': (
                        f'Appointments must be aligned to {SLOT_DURATION_MINUTES}-minute time slots.'
                    )
                }
            )

        if not (DEFAULT_START_TIME <= local_slot.time() < DEFAULT_END_TIME):
            raise ValidationError(
                {
                    'scheduled_at': (
                        f"Appointments are allowed only between {DEFAULT_START_TIME.strftime('%H:%M')} "
                        f"and {DEFAULT_END_TIME.strftime('%H:%M')} with maximum {MAX_PATIENTS_PER_HOUR} patients per hour."
                    )
                }
            )
        return normalized_slot

    def _ensure_staff_can_manage_appointment(self, appointment, user):
        if user.role not in ['doctor', 'admin']:
            raise PermissionDenied('Only doctor or admin can manage this appointment action.')
        if user.role == 'doctor' and appointment.doctor.user_id != user.id:
            raise PermissionDenied('Doctors can only manage their own appointments.')

    @staticmethod
    def _append_action_note(existing_notes, note):
        current = (existing_notes or '').strip()
        if not current:
            return note
        return f"{current}\n{note}"


class AppointmentAdvanceOfferViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AppointmentAdvanceOfferSerializer
    queryset = AppointmentAdvanceOffer.objects.select_related(
        'appointment__patient__user',
        'offered_doctor__user',
    ).all()
    filterset_fields = ['status', 'offered_doctor', 'appointment']
    ordering_fields = ['created_at', 'expires_at', 'offered_slot']

    def get_permissions(self):
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        auto_postpone_unhandled_appointments()
        expire_pending_advance_offers()
        user = self.request.user
        qs = self.queryset
        if user.role == 'patient':
            return qs.filter(appointment__patient__user=user)
        if user.role == 'doctor':
            return qs.filter(offered_doctor__user=user)
        return qs

    def list(self, request, *args, **kwargs):
        expire_pending_advance_offers()
        return super().list(request, *args, **kwargs)

    @action(detail=True, methods=['post'], url_path='respond')
    def respond(self, request, pk=None):
        offer = self.get_object()
        if request.user.role != 'patient':
            raise PermissionDenied('Only patients can respond to appointment advance offers.')

        decision = str(request.data.get('decision', '')).strip().lower()
        if decision in ['accept', 'accepted', 'true', '1', 'yes']:
            accepted = True
        elif decision in ['reject', 'rejected', 'false', '0', 'no']:
            accepted = False
        else:
            raise ValidationError({'decision': 'Decision must be accept or reject.'})

        try:
            respond_to_advance_offer(offer=offer, patient_user=request.user, accepted=accepted)
        except PermissionError as exc:
            raise PermissionDenied(str(exc)) from exc
        except ValueError as exc:
            raise ValidationError({'detail': str(exc)}) from exc

        offer.refresh_from_db()
        return Response(self.get_serializer(offer).data)

from datetime import timedelta

from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import DoctorOperation

OPERATION_GRACE_PERIOD = timedelta(hours=1)


def operation_blocks_at(operation, at_time=None):
    reference = at_time or timezone.now()
    if reference < operation.scheduled_start:
        return False
    return reference < operation.release_at


def get_doctor_blocking_operation(doctor, reference_time=None):
    if not doctor:
        return None

    reference = reference_time or timezone.now()
    return (
        DoctorOperation.objects.select_related('doctor__user', 'medical_record__patient__user')
        .filter(doctor=doctor, scheduled_start__lte=reference, release_at__gt=reference)
        .order_by('scheduled_start')
        .first()
    )


def get_doctor_operation_overlap_for_window(doctor, window_start, window_end, exclude_operation_id=None):
    if not doctor:
        return None

    conflicts = DoctorOperation.objects.select_related('doctor__user').filter(
        doctor=doctor,
        scheduled_start__lt=window_end,
        release_at__gt=window_start,
    )
    if exclude_operation_id:
        conflicts = conflicts.exclude(pk=exclude_operation_id)
    return conflicts.order_by('scheduled_start').first()


def get_doctor_operation_overlap_for_slot(doctor, slot_start, slot_duration_minutes=30):
    window_end = slot_start + timedelta(minutes=slot_duration_minutes)
    return get_doctor_operation_overlap_for_window(doctor, slot_start, window_end)


def validate_operation_schedule_conflicts(doctor, scheduled_start, expected_duration_minutes, exclude_operation_id=None):
    operation_release_at = scheduled_start + timedelta(minutes=int(expected_duration_minutes)) + OPERATION_GRACE_PERIOD

    conflict_operation = get_doctor_operation_overlap_for_window(
        doctor=doctor,
        window_start=scheduled_start,
        window_end=operation_release_at,
        exclude_operation_id=exclude_operation_id,
    )
    if conflict_operation:
        raise ValidationError(
            {
                'scheduled_start': (
                    'This operation conflicts with another operation for the same doctor '
                    f"(#{conflict_operation.id}, starts {timezone.localtime(conflict_operation.scheduled_start).strftime('%Y-%m-%d %H:%M')})."
                )
            }
        )

    from appointments.models import Appointment

    appointment_conflicts = Appointment.objects.filter(
        doctor=doctor,
        status__in=[Appointment.Status.PENDING, Appointment.Status.CONFIRMED],
        scheduled_at__gte=scheduled_start,
        scheduled_at__lt=operation_release_at,
    ).order_by('scheduled_at')

    first_appointment = appointment_conflicts.first()
    if first_appointment:
        raise ValidationError(
            {
                'scheduled_start': (
                    'This operation conflicts with existing appointments. '
                    f"First conflict: appointment #{first_appointment.id} at "
                    f"{timezone.localtime(first_appointment.scheduled_at).strftime('%Y-%m-%d %H:%M')}."
                )
            }
        )


def ensure_doctor_not_blocked_now(doctor, action_label='perform this action'):
    operation = get_doctor_blocking_operation(doctor=doctor)
    if not operation:
        return None

    expected_end = timezone.localtime(operation.expected_end_at).strftime('%Y-%m-%d %H:%M')
    release_at = timezone.localtime(operation.release_at).strftime('%Y-%m-%d %H:%M')
    raise ValidationError(
        {
            'detail': (
                f"Doctor is in operation '{operation.operation_name}' and cannot {action_label}. "
                f'Expected end: {expected_end}. Work unlocks at {release_at} unless the operation is finished manually.'
            )
        }
    )

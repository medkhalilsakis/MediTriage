from datetime import datetime, time, timedelta

from django.db.models import Count
from django.utils import timezone

from doctors.models import DoctorProfile
from medical_records.operations import get_doctor_operation_overlap_for_slot

from .models import Appointment, AppointmentAdvanceOffer

ACTIVE_STATUSES = (Appointment.Status.PENDING, Appointment.Status.CONFIRMED)
SLOT_DURATION_MINUTES = 30
PLANNING_HORIZON_DAYS = 90
MAX_PATIENTS_PER_HOUR = 2
DEFAULT_START_TIME = time(hour=8, minute=0)
DEFAULT_END_TIME = time(hour=16, minute=0)


def assign_doctor_and_slot(requested_department, now=None):
    """Return (doctor, scheduled_at, effective_department) using load-based FIFO scheduling."""
    current_time = now or timezone.now()
    department = requested_department or Appointment.Department.GENERAL_MEDICINE

    candidates = _get_doctor_candidates(department)
    if not candidates and department != Appointment.Department.GENERAL_MEDICINE:
        department = Appointment.Department.GENERAL_MEDICINE
        candidates = _get_doctor_candidates(department)

    if not candidates:
        return None, None, department

    load_map = _get_doctor_load_map(candidates, current_time)

    ranked = []
    for doctor in candidates:
        slot = _find_first_available_slot(doctor, current_time)
        if slot is None:
            continue
        ranked.append((load_map.get(doctor.id, 0), slot, doctor.id, doctor))

    if not ranked:
        return None, None, department

    ranked.sort(key=lambda item: (item[0], item[1], item[2]))
    _, chosen_slot, _, chosen_doctor = ranked[0]
    return chosen_doctor, chosen_slot, department


def find_first_available_slot_for_doctor(doctor, start_from, exclude_appointment_id=None):
    return _find_first_available_slot(
        doctor=doctor,
        current_time=start_from,
        exclude_appointment_id=exclude_appointment_id,
    )


def normalize_slot_datetime(value):
    return _normalize_for_slot(value)


def is_doctor_on_leave(doctor, at_datetime):
    if not doctor:
        return False
    local_value = timezone.localtime(at_datetime)
    leave_ranges = _get_leave_ranges(doctor)
    return _date_in_leave_ranges(local_value.date(), leave_ranges)


def is_doctor_available_for_slot(
    doctor,
    slot_datetime,
    exclude_appointment_id=None,
    exclude_offer_id=None,
):
    if not doctor:
        return False

    if not doctor.user.is_active:
        return False

    slot = _normalize_for_slot(slot_datetime)
    now_local = _normalize_for_slot(timezone.now())

    if slot < now_local or slot.weekday() == 6:
        return False

    if not _is_within_clinic_hours(slot):
        return False

    leave_ranges = _get_leave_ranges(doctor)
    if _date_in_leave_ranges(slot.date(), leave_ranges):
        return False

    if not _is_slot_within_working_windows(doctor, slot):
        return False

    if get_doctor_operation_overlap_for_slot(
        doctor=doctor,
        slot_start=slot,
        slot_duration_minutes=SLOT_DURATION_MINUTES,
    ):
        return False

    appointment_conflict = Appointment.objects.filter(
        doctor=doctor,
        status__in=ACTIVE_STATUSES,
        scheduled_at=slot,
    )
    if exclude_appointment_id:
        appointment_conflict = appointment_conflict.exclude(pk=exclude_appointment_id)
    if appointment_conflict.exists():
        return False

    hour_start = slot.replace(minute=0, second=0, microsecond=0)
    hour_end = hour_start + timedelta(hours=1)

    hourly_appointments = Appointment.objects.filter(
        doctor=doctor,
        status__in=ACTIVE_STATUSES,
        scheduled_at__gte=hour_start,
        scheduled_at__lt=hour_end,
    )
    if exclude_appointment_id:
        hourly_appointments = hourly_appointments.exclude(pk=exclude_appointment_id)

    hourly_appointments_count = hourly_appointments.count()
    if hourly_appointments_count >= MAX_PATIENTS_PER_HOUR:
        return False

    offer_conflict = AppointmentAdvanceOffer.objects.filter(
        offered_doctor=doctor,
        status=AppointmentAdvanceOffer.Status.PENDING,
        offered_slot=slot,
        expires_at__gt=timezone.now(),
    )
    if exclude_offer_id:
        offer_conflict = offer_conflict.exclude(pk=exclude_offer_id)
    if offer_conflict.exists():
        return False

    hourly_offers = AppointmentAdvanceOffer.objects.filter(
        offered_doctor=doctor,
        status=AppointmentAdvanceOffer.Status.PENDING,
        expires_at__gt=timezone.now(),
        offered_slot__gte=hour_start,
        offered_slot__lt=hour_end,
    )
    if exclude_offer_id:
        hourly_offers = hourly_offers.exclude(pk=exclude_offer_id)

    if hourly_appointments_count + hourly_offers.count() >= MAX_PATIENTS_PER_HOUR:
        return False

    return True


def _get_doctor_candidates(department):
    return list(
        DoctorProfile.objects.filter(department=department, user__is_active=True)
        .select_related('user')
        .prefetch_related('availability_slots', 'leave_periods')
    )


def _get_doctor_load_map(doctors, current_time):
    doctor_ids = [doctor.id for doctor in doctors]
    if not doctor_ids:
        return {}

    rows = (
        Appointment.objects.filter(
            doctor_id__in=doctor_ids,
            status__in=ACTIVE_STATUSES,
            scheduled_at__gte=current_time,
        )
        .values('doctor_id')
        .annotate(total=Count('id'))
    )
    return {row['doctor_id']: row['total'] for row in rows}


def _find_first_available_slot(doctor, current_time, exclude_appointment_id=None):
    if not doctor.user.is_active:
        return None

    now_local = _normalize_for_slot(current_time)
    leave_ranges = _get_leave_ranges(doctor)

    occupied_query = Appointment.objects.filter(
        doctor=doctor,
        status__in=ACTIVE_STATUSES,
        scheduled_at__gte=now_local,
    )
    if exclude_appointment_id:
        occupied_query = occupied_query.exclude(pk=exclude_appointment_id)

    occupied = {_normalize_for_slot(item) for item in occupied_query.values_list('scheduled_at', flat=True)}

    reserved_by_offer = {
        _normalize_for_slot(item)
        for item in AppointmentAdvanceOffer.objects.filter(
            offered_doctor=doctor,
            status=AppointmentAdvanceOffer.Status.PENDING,
            expires_at__gt=timezone.now(),
            offered_slot__gte=now_local,
        ).values_list('offered_slot', flat=True)
    }

    base_date = now_local.date()
    for day_offset in range(PLANNING_HORIZON_DAYS):
        day = base_date + timedelta(days=day_offset)

        # Sunday is always a non-working day.
        if day.weekday() == 6:
            continue

        if _date_in_leave_ranges(day, leave_ranges):
            continue

        for window_start, window_end in _working_windows_for_day(doctor, day.weekday()):
            slot = _make_aware(day, window_start)
            slot = _normalize_for_slot(slot)
            if slot < now_local:
                slot = now_local

            end_at = _make_aware(day, window_end)
            while slot < end_at:
                if slot.weekday() == 6:
                    slot += timedelta(minutes=SLOT_DURATION_MINUTES)
                    continue

                if _date_in_leave_ranges(slot.date(), leave_ranges):
                    slot += timedelta(minutes=SLOT_DURATION_MINUTES)
                    continue

                if slot in occupied or slot in reserved_by_offer:
                    slot += timedelta(minutes=SLOT_DURATION_MINUTES)
                    continue

                if get_doctor_operation_overlap_for_slot(
                    doctor=doctor,
                    slot_start=slot,
                    slot_duration_minutes=SLOT_DURATION_MINUTES,
                ):
                    slot += timedelta(minutes=SLOT_DURATION_MINUTES)
                    continue

                return slot

    return None


def _working_windows_for_day(doctor, weekday):
    windows = []
    for slot in doctor.availability_slots.all():
        if not slot.is_active or slot.weekday != weekday:
            continue
        if slot.start_time >= slot.end_time:
            continue

        start_time = max(slot.start_time, DEFAULT_START_TIME)
        end_time = min(slot.end_time, DEFAULT_END_TIME)
        if start_time < end_time:
            windows.append((start_time, end_time))

    if not windows:
        return [(DEFAULT_START_TIME, DEFAULT_END_TIME)]

    windows.sort(key=lambda item: item[0])
    return windows


def _is_slot_within_working_windows(doctor, slot_datetime):
    local_slot = timezone.localtime(slot_datetime)
    weekday = local_slot.weekday()
    if weekday == 6:
        return False

    if not _is_within_clinic_hours(local_slot):
        return False

    slot_time = local_slot.time()
    for start_time, end_time in _working_windows_for_day(doctor, weekday):
        if start_time <= slot_time < end_time:
            return True
    return False


def _is_within_clinic_hours(slot_datetime):
    local_slot = timezone.localtime(slot_datetime)
    slot_time = local_slot.time()
    return DEFAULT_START_TIME <= slot_time < DEFAULT_END_TIME


def _get_leave_ranges(doctor):
    prefetched = getattr(doctor, '_prefetched_objects_cache', {})
    prefetched_leaves = prefetched.get('leave_periods')
    if prefetched_leaves is not None:
        return [(leave.start_date, leave.end_date) for leave in prefetched_leaves if leave.is_active]

    return list(
        doctor.leave_periods.filter(is_active=True).values_list('start_date', 'end_date')
    )


def _date_in_leave_ranges(day, leave_ranges):
    for start_date, end_date in leave_ranges:
        if start_date <= day <= end_date:
            return True
    return False


def _normalize_for_slot(value):
    local_value = timezone.localtime(value).replace(second=0, microsecond=0)
    minute_remainder = local_value.minute % SLOT_DURATION_MINUTES
    if minute_remainder:
        local_value += timedelta(minutes=SLOT_DURATION_MINUTES - minute_remainder)
    return local_value


def _make_aware(day, at_time):
    naive = datetime.combine(day, at_time)
    return timezone.make_aware(naive, timezone.get_current_timezone())

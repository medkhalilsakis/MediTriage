from datetime import datetime, timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone

from doctors.models import DoctorProfile
from notifications.models import Notification

from .models import Appointment, AppointmentAdvanceOffer
from .scheduling import (
    ACTIVE_STATUSES,
    DEFAULT_START_TIME,
    find_first_available_slot_for_doctor,
    is_doctor_available_for_slot,
)

ADVANCE_RESPONSE_WINDOW_MINUTES = 15
AUTO_POSTPONE_AFTER_HOURS = 1


def auto_postpone_unhandled_appointments(now=None):
    """Auto-delay appointments with no doctor/admin action 1 hour after scheduled time."""
    current_time = now or timezone.now()
    cutoff = current_time - timedelta(hours=AUTO_POSTPONE_AFTER_HOURS)

    expire_pending_advance_offers(now=current_time)

    candidates = list(
        Appointment.objects.select_related('patient__user', 'doctor__user')
        .filter(
            status__in=ACTIVE_STATUSES,
            scheduled_at__lte=cutoff,
            last_staff_action_at__isnull=True,
        )
        .order_by('scheduled_at', 'id')
    )

    postponed = 0
    for appointment in candidates:
        with transaction.atomic():
            locked_appointment = (
                Appointment.objects.select_for_update()
                .select_related('patient__user', 'doctor__user')
                .filter(
                    pk=appointment.pk,
                    status__in=ACTIVE_STATUSES,
                    last_staff_action_at__isnull=True,
                )
                .first()
            )

            if not locked_appointment:
                continue

            if locked_appointment.scheduled_at > cutoff:
                continue

            old_slot = locked_appointment.scheduled_at
            new_slot = _compute_auto_postponed_slot(old_slot, current_time)

            if not is_doctor_available_for_slot(
                doctor=locked_appointment.doctor,
                slot_datetime=new_slot,
                exclude_appointment_id=locked_appointment.id,
            ):
                fallback_slot = find_first_available_slot_for_doctor(
                    doctor=locked_appointment.doctor,
                    start_from=new_slot,
                    exclude_appointment_id=locked_appointment.id,
                )
                if not fallback_slot:
                    continue
                new_slot = fallback_slot

            close_pending_offers_for_appointment(locked_appointment)

            locked_appointment.scheduled_at = new_slot
            locked_appointment.status = Appointment.Status.CONFIRMED
            locked_appointment.notes = _append_note(
                locked_appointment.notes,
                (
                    f"Automatically postponed to {timezone.localtime(new_slot).strftime('%Y-%m-%d %H:%M')} "
                    "because no doctor/admin action was recorded within 1 hour after the original schedule."
                ),
            )
            locked_appointment.save(update_fields=['scheduled_at', 'status', 'notes', 'updated_at'])

        postponed += 1
        trigger_waitlist_for_freed_slot(doctor=locked_appointment.doctor, freed_slot=old_slot, actor=None)
        _notify_patient(
            locked_appointment,
            title='Appointment auto-postponed',
            message=(
                f"Your appointment was automatically postponed to "
                f"{timezone.localtime(locked_appointment.scheduled_at).strftime('%Y-%m-%d %H:%M')} "
                "because no doctor/admin action was recorded on time."
            ),
        )
        _notify_doctor(
            locked_appointment.doctor,
            title='Appointment auto-postponed by system',
            message=(
                f"Appointment #{locked_appointment.id} was auto-postponed to "
                f"{timezone.localtime(locked_appointment.scheduled_at).strftime('%Y-%m-%d %H:%M')} "
                "after 1 hour without doctor/admin action."
            ),
        )

    return {'postponed': postponed}


def redistribute_appointments_for_leave(leave, actor=None):
    """Reallocate or postpone active appointments affected by a doctor's leave."""
    expire_pending_advance_offers()

    affected_appointments = list(
        Appointment.objects.select_related('patient__user', 'doctor__user')
        .filter(
            doctor=leave.doctor,
            status__in=ACTIVE_STATUSES,
            scheduled_at__date__gte=leave.start_date,
            scheduled_at__date__lte=leave.end_date,
        )
        .order_by('scheduled_at', 'id')
    )

    if not affected_appointments:
        return {'reassigned': 0, 'postponed': 0, 'unhandled': 0}

    candidate_doctors = list(
        DoctorProfile.objects.exclude(pk=leave.doctor_id)
        .select_related('user')
        .prefetch_related('availability_slots', 'leave_periods')
    )

    distribution_counter = {}
    reassigned = 0
    postponed = 0
    unhandled = 0

    postpone_from = _make_aware(leave.end_date + timedelta(days=1), DEFAULT_START_TIME)

    for appointment in affected_appointments:
        close_pending_offers_for_appointment(appointment)

        available_doctors = [
            doctor
            for doctor in candidate_doctors
            if is_doctor_available_for_slot(doctor, appointment.scheduled_at)
        ]

        selected_doctor = _select_balanced_doctor(available_doctors, distribution_counter)
        if selected_doctor:
            previous_doctor = appointment.doctor
            appointment.doctor = selected_doctor
            appointment.department = selected_doctor.department
            appointment.status = Appointment.Status.CONFIRMED
            appointment.notes = _append_note(
                appointment.notes,
                f"Automatically reassigned from Dr. {previous_doctor.user.email} due to leave {leave.start_date} to {leave.end_date}.",
            )
            appointment.save(update_fields=['doctor', 'department', 'status', 'notes', 'updated_at'])

            distribution_counter[selected_doctor.id] = distribution_counter.get(selected_doctor.id, 0) + 1
            reassigned += 1

            _notify_patient(
                appointment,
                title='Appointment reassigned',
                message=(
                    f"Your appointment has been transferred to Dr. {selected_doctor.user.email} "
                    f"on {timezone.localtime(appointment.scheduled_at).strftime('%Y-%m-%d %H:%M')} "
                    f"because your previous doctor is on leave."
                ),
            )
            _notify_doctor(
                selected_doctor,
                title='New transferred appointment',
                message=(
                    f"Appointment #{appointment.id} was transferred to you for "
                    f"{timezone.localtime(appointment.scheduled_at).strftime('%Y-%m-%d %H:%M')}."
                ),
            )
            continue

        new_slot = find_first_available_slot_for_doctor(
            doctor=leave.doctor,
            start_from=max(postpone_from, timezone.now()),
            exclude_appointment_id=appointment.id,
        )
        if not new_slot:
            unhandled += 1
            continue

        old_slot = appointment.scheduled_at
        appointment.scheduled_at = new_slot
        appointment.status = Appointment.Status.CONFIRMED
        appointment.notes = _append_note(
            appointment.notes,
            f"Automatically postponed from {timezone.localtime(old_slot).strftime('%Y-%m-%d %H:%M')} due to doctor leave.",
        )
        appointment.save(update_fields=['scheduled_at', 'status', 'notes', 'updated_at'])
        postponed += 1

        _notify_patient(
            appointment,
            title='Appointment postponed',
            message=(
                f"Your appointment was postponed to "
                f"{timezone.localtime(new_slot).strftime('%Y-%m-%d %H:%M')} "
                f"because your doctor is on leave and no replacement was available."
            ),
        )

    return {'reassigned': reassigned, 'postponed': postponed, 'unhandled': unhandled}


def trigger_waitlist_for_freed_slot(doctor, freed_slot, actor=None):
    """Offer a newly freed slot to the next patient in waiting order for that doctor."""
    if not doctor or not freed_slot:
        return None

    slot = timezone.localtime(freed_slot).replace(second=0, microsecond=0)
    if slot <= timezone.now():
        return None

    expire_pending_advance_offers()
    return _offer_next_patient_for_slot(doctor=doctor, freed_slot=slot, actor=actor)


def expire_pending_advance_offers(now=None):
    current_time = now or timezone.now()
    expired_offers = list(
        AppointmentAdvanceOffer.objects.select_related('appointment', 'offered_doctor')
        .filter(
            status=AppointmentAdvanceOffer.Status.PENDING,
            expires_at__lte=current_time,
        )
        .order_by('expires_at', 'id')
    )

    for offer in expired_offers:
        with transaction.atomic():
            locked_offer = (
                AppointmentAdvanceOffer.objects.select_for_update()
                .select_related('appointment__patient__user', 'offered_doctor__user')
                .filter(pk=offer.pk, status=AppointmentAdvanceOffer.Status.PENDING)
                .first()
            )
            if not locked_offer:
                continue
            if locked_offer.expires_at > current_time:
                continue

            locked_offer.status = AppointmentAdvanceOffer.Status.EXPIRED
            locked_offer.responded_at = current_time
            locked_offer.save(update_fields=['status', 'responded_at', 'updated_at'])

        _notify_patient(
            locked_offer.appointment,
            title='Advance offer expired',
            message=(
                f"The earlier-slot offer for appointment #{locked_offer.appointment_id} expired. "
                "You keep your current appointment time."
            ),
        )

        _offer_next_patient_for_slot(
            doctor=locked_offer.offered_doctor,
            freed_slot=locked_offer.offered_slot,
            actor=None,
            extra_excluded_appointment_ids=[locked_offer.appointment_id],
        )


def respond_to_advance_offer(offer, patient_user, accepted):
    with transaction.atomic():
        locked_offer = (
            AppointmentAdvanceOffer.objects.select_for_update()
            .select_related('appointment__patient__user', 'offered_doctor__user')
            .filter(pk=offer.pk)
            .first()
        )
        if not locked_offer:
            raise ValueError('Advance offer not found.')

        appointment = locked_offer.appointment
        if appointment.patient.user_id != patient_user.id:
            raise PermissionError('You can only answer offers for your own appointments.')

        if locked_offer.status != AppointmentAdvanceOffer.Status.PENDING:
            raise ValueError('This offer is no longer pending.')

        if locked_offer.expires_at <= timezone.now():
            locked_offer.status = AppointmentAdvanceOffer.Status.EXPIRED
            locked_offer.responded_at = timezone.now()
            locked_offer.save(update_fields=['status', 'responded_at', 'updated_at'])
            _offer_next_patient_for_slot(
                doctor=locked_offer.offered_doctor,
                freed_slot=locked_offer.offered_slot,
                actor=patient_user,
                extra_excluded_appointment_ids=[appointment.id],
            )
            raise ValueError('This offer has expired.')

        if accepted:
            if not is_doctor_available_for_slot(
                doctor=locked_offer.offered_doctor,
                slot_datetime=locked_offer.offered_slot,
                exclude_appointment_id=appointment.id,
                exclude_offer_id=locked_offer.id,
            ):
                locked_offer.status = AppointmentAdvanceOffer.Status.EXPIRED
                locked_offer.responded_at = timezone.now()
                locked_offer.save(update_fields=['status', 'responded_at', 'updated_at'])
                _offer_next_patient_for_slot(
                    doctor=locked_offer.offered_doctor,
                    freed_slot=locked_offer.offered_slot,
                    actor=patient_user,
                    extra_excluded_appointment_ids=[appointment.id],
                )
                raise ValueError('Slot is no longer available.')

            old_slot = appointment.scheduled_at
            appointment.scheduled_at = locked_offer.offered_slot
            appointment.doctor = locked_offer.offered_doctor
            appointment.department = locked_offer.offered_doctor.department
            appointment.status = Appointment.Status.CONFIRMED
            appointment.notes = _append_note(
                appointment.notes,
                f"Patient accepted an earlier slot at {timezone.localtime(locked_offer.offered_slot).strftime('%Y-%m-%d %H:%M')}.",
            )
            appointment.save(update_fields=['scheduled_at', 'doctor', 'department', 'status', 'notes', 'updated_at'])

            locked_offer.status = AppointmentAdvanceOffer.Status.ACCEPTED
            locked_offer.responded_at = timezone.now()
            locked_offer.save(update_fields=['status', 'responded_at', 'updated_at'])

            _notify_patient(
                appointment,
                title='Appointment advanced',
                message=(
                    f"Your appointment has been moved earlier to "
                    f"{timezone.localtime(appointment.scheduled_at).strftime('%Y-%m-%d %H:%M')}."
                ),
            )
            _notify_doctor(
                appointment.doctor,
                title='Appointment advanced by patient',
                message=(
                    f"Patient {appointment.patient.user.email} accepted an earlier slot for appointment "
                    f"#{appointment.id}."
                ),
            )

            trigger_waitlist_for_freed_slot(doctor=appointment.doctor, freed_slot=old_slot, actor=patient_user)
            return locked_offer

        locked_offer.status = AppointmentAdvanceOffer.Status.REJECTED
        locked_offer.responded_at = timezone.now()
        locked_offer.save(update_fields=['status', 'responded_at', 'updated_at'])

    _offer_next_patient_for_slot(
        doctor=offer.offered_doctor,
        freed_slot=offer.offered_slot,
        actor=patient_user,
        extra_excluded_appointment_ids=[offer.appointment_id],
    )
    return offer


def close_pending_offers_for_appointment(appointment):
    AppointmentAdvanceOffer.objects.filter(
        appointment=appointment,
        status=AppointmentAdvanceOffer.Status.PENDING,
    ).update(status=AppointmentAdvanceOffer.Status.EXPIRED, responded_at=timezone.now())


def _offer_next_patient_for_slot(doctor, freed_slot, actor=None, extra_excluded_appointment_ids=None):
    now = timezone.now()

    existing_pending = AppointmentAdvanceOffer.objects.filter(
        offered_doctor=doctor,
        offered_slot=freed_slot,
        status=AppointmentAdvanceOffer.Status.PENDING,
        expires_at__gt=now,
    ).first()
    if existing_pending:
        return existing_pending

    slot_is_taken = Appointment.objects.filter(
        doctor=doctor,
        status__in=ACTIVE_STATUSES,
        scheduled_at=freed_slot,
    ).exists()
    if slot_is_taken:
        return None

    excluded_ids = set(extra_excluded_appointment_ids or [])
    historical_offers = AppointmentAdvanceOffer.objects.filter(
        offered_doctor=doctor,
        offered_slot=freed_slot,
        status__in=[AppointmentAdvanceOffer.Status.REJECTED, AppointmentAdvanceOffer.Status.EXPIRED],
    ).values_list('appointment_id', flat=True)
    excluded_ids.update(historical_offers)

    pending_offer_appointments = AppointmentAdvanceOffer.objects.filter(
        status=AppointmentAdvanceOffer.Status.PENDING,
        expires_at__gt=now,
    ).values_list('appointment_id', flat=True)

    candidate = (
        Appointment.objects.select_related('patient__user', 'doctor__user')
        .filter(
            doctor=doctor,
            status__in=ACTIVE_STATUSES,
            scheduled_at__gt=freed_slot,
        )
        .exclude(pk__in=excluded_ids)
        .exclude(pk__in=pending_offer_appointments)
        .order_by('scheduled_at', 'id')
        .first()
    )
    if not candidate:
        return None

    expires_at = now + timedelta(minutes=ADVANCE_RESPONSE_WINDOW_MINUTES)
    try:
        with transaction.atomic():
            offer = AppointmentAdvanceOffer.objects.create(
                appointment=candidate,
                offered_doctor=doctor,
                offered_slot=freed_slot,
                status=AppointmentAdvanceOffer.Status.PENDING,
                expires_at=expires_at,
                requested_by=actor,
            )
    except IntegrityError:
        return None

    _notify_patient(
        candidate,
        title='Earlier appointment slot available',
        message=(
            f"An earlier slot is available at {timezone.localtime(freed_slot).strftime('%Y-%m-%d %H:%M')}. "
            f"Please accept or reject within {ADVANCE_RESPONSE_WINDOW_MINUTES} minutes."
        ),
    )

    return offer


def _compute_auto_postponed_slot(original_slot, now):
    next_slot = _next_auto_postpone_slot(original_slot)
    while next_slot + timedelta(hours=AUTO_POSTPONE_AFTER_HOURS) <= now:
        next_slot = _next_auto_postpone_slot(next_slot)
    return next_slot


def _next_auto_postpone_slot(slot_datetime):
    delayed = timezone.localtime(slot_datetime).replace(second=0, microsecond=0) + timedelta(days=1)
    if delayed.weekday() == 6:
        delayed += timedelta(days=1)
    return delayed


def _select_balanced_doctor(doctors, distribution_counter):
    if not doctors:
        return None

    doctors = sorted(
        doctors,
        key=lambda doctor: (distribution_counter.get(doctor.id, 0), doctor.id),
    )
    return doctors[0]


def _make_aware(day, at_time):
    naive = datetime.combine(day, at_time)
    return timezone.make_aware(naive, timezone.get_current_timezone())


def _append_note(existing_notes, extra_note):
    existing = (existing_notes or '').strip()
    if not existing:
        return extra_note
    return f"{existing}\n{extra_note}"


def _notify_patient(appointment, title, message):
    Notification.objects.create(
        recipient=appointment.patient.user,
        notification_type=Notification.Type.APPOINTMENT,
        title=title,
        message=message,
    )


def _notify_doctor(doctor, title, message):
    Notification.objects.create(
        recipient=doctor.user,
        notification_type=Notification.Type.APPOINTMENT,
        title=title,
        message=message,
    )

from django.db import transaction
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from authentication.permissions import IsAdmin
from appointments.workflows import redistribute_appointments_for_leave
from notifications.models import Notification

from .models import DoctorAvailabilitySlot, DoctorLeave, DoctorProfile
from .serializers import DoctorAvailabilitySlotSerializer, DoctorLeaveSerializer, DoctorProfileSerializer


class DoctorProfileViewSet(viewsets.ModelViewSet):
	serializer_class = DoctorProfileSerializer
	queryset = DoctorProfile.objects.select_related('user').prefetch_related('availability_slots').all()
	filterset_fields = ['specialization', 'department']
	search_fields = ['user__email', 'user__first_name', 'user__last_name', 'specialization', 'department', 'license_number']
	ordering_fields = ['created_at', 'updated_at', 'years_of_experience']

	def get_permissions(self):
		if self.action in ['destroy']:
			permission_classes = [permissions.IsAuthenticated, IsAdmin]
		else:
			permission_classes = [permissions.IsAuthenticated]
		return [permission() for permission in permission_classes]

	def get_queryset(self):
		return self.queryset

	def perform_create(self, serializer):
		if self.request.user.role not in ['admin', 'doctor']:
			raise PermissionDenied('Only doctor or admin can create doctor profiles.')
		serializer.save()


class DoctorAvailabilitySlotViewSet(viewsets.ModelViewSet):
	serializer_class = DoctorAvailabilitySlotSerializer
	queryset = DoctorAvailabilitySlot.objects.select_related('doctor', 'doctor__user').all()
	filterset_fields = ['doctor', 'weekday', 'is_active']
	ordering_fields = ['weekday', 'start_time', 'created_at']

	def get_permissions(self):
		return [permissions.IsAuthenticated()]

	def get_queryset(self):
		user = self.request.user
		if user.role == 'doctor':
			return self.queryset.filter(doctor__user=user)
		return self.queryset

	def perform_create(self, serializer):
		user = self.request.user
		if user.role == 'doctor':
			serializer.save(doctor=user.doctor_profile)
			return
		if user.role == 'admin':
			serializer.save()
			return
		raise PermissionDenied('Only doctor or admin can create availability slots.')


class DoctorLeaveViewSet(viewsets.ModelViewSet):
	serializer_class = DoctorLeaveSerializer
	queryset = DoctorLeave.objects.select_related('doctor', 'doctor__user', 'created_by', 'reviewed_by').all()
	filterset_fields = ['doctor', 'status', 'is_active', 'start_date', 'end_date']
	ordering_fields = ['start_date', 'end_date', 'created_at', 'updated_at']

	def get_permissions(self):
		return [permissions.IsAuthenticated()]

	def get_queryset(self):
		user = self.request.user
		if user.role == 'admin':
			return self.queryset
		if user.role == 'doctor':
			doctor_profile = self._resolve_doctor_profile(user)
			if not doctor_profile:
				return self.queryset.none()
			return self.queryset.filter(doctor=doctor_profile)
		return self.queryset.none()

	def _resolve_doctor_profile(self, user):
		return DoctorProfile.objects.filter(user=user).first()

	def _run_leave_impact_rules(self, leave):
		if leave.status != DoctorLeave.Status.APPROVED or not leave.is_active:
			return
		redistribute_appointments_for_leave(leave=leave, actor=self.request.user)

	def _validate_approval_overlap(self, leave):
		overlap = DoctorLeave.objects.filter(
			doctor=leave.doctor,
			is_active=True,
			start_date__lte=leave.end_date,
			end_date__gte=leave.start_date,
		).exclude(pk=leave.pk)
		if overlap.exists():
			raise ValidationError(
				{'detail': 'Another approved leave already overlaps this date range for the doctor.'}
			)

	def _notify_leave_review(self, leave, approved):
		review_status = 'approved' if approved else 'rejected'
		message = (
			f"Your leave request from {leave.start_date} to {leave.end_date} was {review_status} "
			f"by admin {self.request.user.email}."
		)
		if leave.review_note:
			message = f"{message} Note: {leave.review_note}"

		recipient_ids = {leave.doctor.user_id}
		if leave.created_by_id and leave.created_by and leave.created_by.role == 'doctor':
			recipient_ids.add(leave.created_by_id)

		for recipient_id in recipient_ids:
			Notification.objects.create(
				recipient_id=recipient_id,
				notification_type=Notification.Type.SYSTEM,
				title=f"Leave request {review_status}",
				message=message,
			)

	@action(detail=True, methods=['post'], url_path='cancel')
	def cancel(self, request, pk=None):
		leave = self.get_object()
		user = request.user

		if user.role == 'doctor':
			doctor_profile = self._resolve_doctor_profile(user)
			if not doctor_profile:
				raise ValidationError({'doctor': 'Doctor profile is missing for this account.'})
			if leave.doctor_id != doctor_profile.id:
				raise PermissionDenied('Doctors can only cancel their own leave requests.')
		elif user.role != 'admin':
			raise PermissionDenied('Only doctor or admin can cancel leave requests.')

		if leave.status == DoctorLeave.Status.CANCELLED and not leave.is_active:
			return Response(self.get_serializer(leave).data, status=status.HTTP_200_OK)

		leave.status = DoctorLeave.Status.CANCELLED
		leave.is_active = False
		if user.role == 'admin':
			leave.reviewed_by = user
			leave.reviewed_at = timezone.now()
		if not leave.review_note:
			leave.review_note = f"Cancelled by {user.role} {user.email}."

		leave.save(update_fields=['status', 'is_active', 'reviewed_by', 'reviewed_at', 'review_note', 'updated_at'])

		Notification.objects.create(
			recipient=leave.doctor.user,
			notification_type=Notification.Type.SYSTEM,
			title='Leave request cancelled',
			message=(
				f"Leave request from {leave.start_date} to {leave.end_date} was cancelled by "
				f"{user.role} {user.email}."
			),
		)

		return Response(self.get_serializer(leave).data, status=status.HTTP_200_OK)

	def perform_create(self, serializer):
		user = self.request.user
		if user.role == 'doctor':
			doctor_profile = self._resolve_doctor_profile(user)
			if not doctor_profile:
				raise ValidationError({'doctor': 'Doctor profile is missing for this account.'})
			serializer.save(
				doctor=doctor_profile,
				created_by=user,
				status=DoctorLeave.Status.PENDING,
				is_active=False,
				reviewed_by=None,
				reviewed_at=None,
				review_note='',
			)
			return

		if user.role == 'admin':
			if not serializer.validated_data.get('doctor'):
				raise ValidationError({'doctor': 'This field is required for admin leave creation.'})
			serializer.save(
				created_by=user,
				status=DoctorLeave.Status.PENDING,
				is_active=False,
				reviewed_by=None,
				reviewed_at=None,
				review_note='',
			)
			return

		raise PermissionDenied('Only doctor or admin can create leave periods.')

	def perform_update(self, serializer):
		user = self.request.user
		if user.role not in ['doctor', 'admin']:
			raise PermissionDenied('Only doctor or admin can update leave periods.')

		leave = serializer.instance
		if leave.status != DoctorLeave.Status.PENDING:
			raise ValidationError({'detail': 'Only pending leave requests can be modified.'})

		if user.role == 'doctor':
			doctor_profile = self._resolve_doctor_profile(user)
			if not doctor_profile:
				raise ValidationError({'doctor': 'Doctor profile is missing for this account.'})
			if leave.doctor_id != doctor_profile.id:
				raise PermissionDenied('Doctors can only update their own leave requests.')
			serializer.save(
				doctor=doctor_profile,
				status=DoctorLeave.Status.PENDING,
				is_active=False,
				reviewed_by=None,
				reviewed_at=None,
			)
			return

		serializer.save(
			status=DoctorLeave.Status.PENDING,
			is_active=False,
			reviewed_by=None,
			reviewed_at=None,
		)

	@action(detail=True, methods=['post'], url_path='approve')
	def approve(self, request, pk=None):
		if request.user.role != 'admin':
			raise PermissionDenied('Only admin can approve leave requests.')

		leave = self.get_object()
		if leave.status != DoctorLeave.Status.PENDING:
			raise ValidationError({'detail': 'Only pending leave requests can be approved.'})

		review_note = str(request.data.get('review_note', '') or '').strip()
		self._validate_approval_overlap(leave)

		with transaction.atomic():
			leave.status = DoctorLeave.Status.APPROVED
			leave.is_active = True
			leave.reviewed_by = request.user
			leave.reviewed_at = timezone.now()
			leave.review_note = review_note
			leave.save(
				update_fields=['status', 'is_active', 'reviewed_by', 'reviewed_at', 'review_note', 'updated_at']
			)
			self._run_leave_impact_rules(leave)

		self._notify_leave_review(leave, approved=True)

		return Response(self.get_serializer(leave).data, status=status.HTTP_200_OK)

	@action(detail=True, methods=['post'], url_path='reject')
	def reject(self, request, pk=None):
		if request.user.role != 'admin':
			raise PermissionDenied('Only admin can reject leave requests.')

		leave = self.get_object()
		if leave.status != DoctorLeave.Status.PENDING:
			raise ValidationError({'detail': 'Only pending leave requests can be rejected.'})

		leave.status = DoctorLeave.Status.REJECTED
		leave.is_active = False
		leave.reviewed_by = request.user
		leave.reviewed_at = timezone.now()
		leave.review_note = str(request.data.get('review_note', '') or '').strip()
		with transaction.atomic():
			leave.save(update_fields=['status', 'is_active', 'reviewed_by', 'reviewed_at', 'review_note', 'updated_at'])

		self._notify_leave_review(leave, approved=False)

		return Response(self.get_serializer(leave).data, status=status.HTTP_200_OK)

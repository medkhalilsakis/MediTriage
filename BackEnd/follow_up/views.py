from rest_framework import permissions, viewsets

from .models import FollowUp, FollowUpAlert
from .serializers import FollowUpAlertSerializer, FollowUpSerializer


class FollowUpViewSet(viewsets.ModelViewSet):
	serializer_class = FollowUpSerializer
	queryset = FollowUp.objects.select_related('patient__user', 'doctor__user', 'consultation').prefetch_related('alerts').all()
	filterset_fields = ['patient', 'doctor', 'status']
	search_fields = ['notes', 'patient__user__email', 'doctor__user__email']
	ordering_fields = ['scheduled_at', 'created_at', 'updated_at']

	def get_permissions(self):
		return [permissions.IsAuthenticated()]

	def get_queryset(self):
		user = self.request.user
		qs = self.queryset
		if user.role == 'patient':
			return qs.filter(patient__user=user)
		if user.role == 'doctor':
			return qs.filter(doctor__user=user)
		return qs


class FollowUpAlertViewSet(viewsets.ModelViewSet):
	serializer_class = FollowUpAlertSerializer
	queryset = FollowUpAlert.objects.select_related('follow_up', 'follow_up__patient__user', 'follow_up__doctor__user').all()
	filterset_fields = ['follow_up', 'alert_type', 'status']
	ordering_fields = ['scheduled_at', 'created_at']

	def get_permissions(self):
		return [permissions.IsAuthenticated()]

	def get_queryset(self):
		user = self.request.user
		qs = self.queryset
		if user.role == 'patient':
			return qs.filter(follow_up__patient__user=user)
		if user.role == 'doctor':
			return qs.filter(follow_up__doctor__user=user)
		return qs

from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Notification
from .serializers import NotificationSerializer


class NotificationViewSet(viewsets.ModelViewSet):
	serializer_class = NotificationSerializer
	queryset = Notification.objects.select_related('recipient').all()
	filterset_fields = ['notification_type', 'is_read', 'recipient']
	search_fields = ['title', 'message', 'recipient__email']
	ordering_fields = ['created_at']

	def get_permissions(self):
		return [permissions.IsAuthenticated()]

	def get_queryset(self):
		user = self.request.user
		qs = self.queryset
		if user.role == 'admin':
			return qs
		return qs.filter(recipient=user)

	@action(detail=False, methods=['post'], url_path='mark-all-read')
	def mark_all_read(self, request):
		count = self.get_queryset().filter(is_read=False).update(is_read=True)
		return Response({'updated': count})

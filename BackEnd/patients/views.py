from rest_framework import permissions, viewsets
from rest_framework.exceptions import PermissionDenied

from authentication.permissions import IsAdmin

from .models import PatientProfile
from .serializers import PatientProfileSerializer


class PatientProfileViewSet(viewsets.ModelViewSet):
    serializer_class = PatientProfileSerializer
    queryset = PatientProfile.objects.select_related('user').all()
    filterset_fields = ['gender', 'blood_group']
    search_fields = ['user__email', 'user__first_name', 'user__last_name', 'allergies']
    ordering_fields = ['created_at', 'updated_at']

    def get_permissions(self):
        if self.action in ['destroy']:
            permission_classes = [permissions.IsAuthenticated, IsAdmin]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        user = self.request.user
        qs = self.queryset
        if user.role == 'patient':
            return qs.filter(user=user)
        return qs

    def perform_create(self, serializer):
        if self.request.user.role not in ['admin', 'doctor']:
            raise PermissionDenied('Only doctor or admin can create patient profiles.')
        serializer.save()

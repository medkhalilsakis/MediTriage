from django.db.models import Count
from django.db.models.functions import TruncWeek
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenRefreshView

from appointments.models import Appointment
from medical_records.models import Consultation
from prescriptions.models import Prescription
from patients.models import PatientProfile
from doctors.models import DoctorProfile

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
        return Response(AuthResponseSerializer.build(user), status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        return Response(AuthResponseSerializer.build(serializer.validated_data['user']))


class AccountMeView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = AccountMeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class AdminStatsView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
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

        data = {
            'users_total': request.user.__class__.objects.count(),
            'patients_total': PatientProfile.objects.count(),
            'doctors_total': DoctorProfile.objects.count(),
            'appointments_total': Appointment.objects.count(),
            'consultations_total': Consultation.objects.count(),
            'prescriptions_total': Prescription.objects.count(),
            'consultations_by_week': list(consultations_by_week),
            'urgency_split': list(urgency_split),
        }
        return Response(data)


class JWTRefreshView(TokenRefreshView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

from rest_framework.routers import DefaultRouter

from .views import (
	ConsultationViewSet,
	MedicalDocumentRequestViewSet,
	MedicalDocumentViewSet,
	MedicalRecordViewSet,
)

router = DefaultRouter()
router.register('records', MedicalRecordViewSet, basename='medical-record')
router.register('consultations', ConsultationViewSet, basename='consultation')
router.register('requests', MedicalDocumentRequestViewSet, basename='medical-document-request')
router.register('documents', MedicalDocumentViewSet, basename='medical-document')

urlpatterns = router.urls

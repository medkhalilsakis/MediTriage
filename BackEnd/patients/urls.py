from rest_framework.routers import DefaultRouter

from .views import PatientProfileViewSet

router = DefaultRouter()
router.register('', PatientProfileViewSet, basename='patient-profile')

urlpatterns = router.urls

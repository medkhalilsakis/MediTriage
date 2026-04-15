from rest_framework.routers import DefaultRouter

from .views import DoctorAvailabilitySlotViewSet, DoctorLeaveViewSet, DoctorProfileViewSet

router = DefaultRouter()
router.register('profiles', DoctorProfileViewSet, basename='doctor-profile')
router.register('availability', DoctorAvailabilitySlotViewSet, basename='doctor-availability')
router.register('leaves', DoctorLeaveViewSet, basename='doctor-leave')

urlpatterns = router.urls

from rest_framework.routers import DefaultRouter

from .views import AppointmentAdvanceOfferViewSet, AppointmentViewSet

router = DefaultRouter()
router.register('advance-offers', AppointmentAdvanceOfferViewSet, basename='appointment-advance-offer')
router.register('', AppointmentViewSet, basename='appointment')

urlpatterns = router.urls

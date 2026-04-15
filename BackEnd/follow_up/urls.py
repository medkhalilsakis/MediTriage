from rest_framework.routers import DefaultRouter

from .views import FollowUpAlertViewSet, FollowUpViewSet

router = DefaultRouter()
router.register('', FollowUpViewSet, basename='follow-up')
router.register('alerts', FollowUpAlertViewSet, basename='follow-up-alert')

urlpatterns = router.urls

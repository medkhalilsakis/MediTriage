from rest_framework.routers import DefaultRouter

from .views import ChatbotSessionViewSet

router = DefaultRouter()
router.register('sessions', ChatbotSessionViewSet, basename='chatbot-session')

urlpatterns = router.urls

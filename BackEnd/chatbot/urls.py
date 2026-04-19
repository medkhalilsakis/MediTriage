from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import ChatbotSessionViewSet, PublicChatbotMessageView

router = DefaultRouter()
router.register('sessions', ChatbotSessionViewSet, basename='chatbot-session')

urlpatterns = [
	path('public/message/', PublicChatbotMessageView.as_view(), name='chatbot-public-message'),
	*router.urls,
]

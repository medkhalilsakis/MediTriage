from django.urls import path

from .views import (
    MessagingContactsView,
    MessagingConversationMessagesView,
    MessagingConversationsView,
    MessagingPresenceHeartbeatView,
    MessagingSummaryView,
)

urlpatterns = [
    path('contacts/', MessagingContactsView.as_view(), name='messaging-contacts'),
    path('conversations/', MessagingConversationsView.as_view(), name='messaging-conversations'),
    path(
        'conversations/<int:conversation_id>/messages/',
        MessagingConversationMessagesView.as_view(),
        name='messaging-conversation-messages',
    ),
    path('presence/heartbeat/', MessagingPresenceHeartbeatView.as_view(), name='messaging-heartbeat'),
    path('summary/', MessagingSummaryView.as_view(), name='messaging-summary'),
]

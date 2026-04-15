from django.urls import path

from .views import AccountMeView, AdminStatsView, JWTRefreshView, LoginView, RegisterView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='auth-register'),
    path('login/', LoginView.as_view(), name='auth-login'),
    path('me/', AccountMeView.as_view(), name='auth-me'),
    path('token/refresh/', JWTRefreshView.as_view(), name='token-refresh'),
    path('admin/stats/', AdminStatsView.as_view(), name='admin-stats'),
]

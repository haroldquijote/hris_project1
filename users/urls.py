from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,   # Handles login (returns access + refresh tokens)
    TokenRefreshView,      # Exchanges a valid refresh token for a new access token
    TokenBlacklistView,    # Logout – blacklists a refresh token so it can't be reused
    TokenVerifyView,       # Verifies whether an access token is still valid
)
from .views import CurrentUserView, ChangePasswordView, AssistantListView, AssistantPermissionsView, ToggleAssistantActiveView

# ---------------------------------------------------------------
# Authentication & User URLs
# All paths are relative to /api/auth/ (set in the main urls.py)
# ---------------------------------------------------------------
urlpatterns = [
    path('login/', TokenObtainPairView.as_view(), name='login'),
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('logout/', TokenBlacklistView.as_view(), name='token_blacklist'),
    path('verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('me/', CurrentUserView.as_view(), name='current_user'),
    path('change-password/', ChangePasswordView.as_view(), name='change_password'),
    path('assistants/', AssistantListView.as_view(), name='assistant-list'),
    path('assistants/<int:user_id>/permissions/', AssistantPermissionsView.as_view(), name='assistant-permissions'),
    path('assistants/<int:user_id>/toggle-active/', ToggleAssistantActiveView.as_view(), name='assistant-toggle-active'),
]
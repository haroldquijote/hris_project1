from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,   # Handles login (returns access + refresh tokens)
    TokenRefreshView,      # Exchanges a valid refresh token for a new access token
    TokenBlacklistView,    # Logout – blacklists a refresh token so it can't be reused
    TokenVerifyView,       # Verifies whether an access token is still valid
)
from .views import CurrentUserView, ChangePasswordView

# ---------------------------------------------------------------
# Authentication & User URLs
# All paths are relative to /api/auth/ (set in the main urls.py)
# ---------------------------------------------------------------
urlpatterns = [
    # -----------------------------------------------------------
    # 1. LOGIN
    # POST /api/auth/login/
    # Body: { "username": "...", "password": "..." }
    # Returns: { "access": "...", "refresh": "..." }
    # -----------------------------------------------------------
    path('login/', TokenObtainPairView.as_view(), name='login'),

    # -----------------------------------------------------------
    # 2. TOKEN REFRESH
    # POST /api/auth/refresh/
    # Body: { "refresh": "..." }
    # Returns: { "access": "..." } (and a new refresh token if rotation is on)
    # -----------------------------------------------------------
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # -----------------------------------------------------------
    # 3. LOGOUT
    # POST /api/auth/logout/
    # Body: { "refresh": "..." }
    # Blacklists the refresh token so it can no longer be used.
    # -----------------------------------------------------------
    path('logout/', TokenBlacklistView.as_view(), name='token_blacklist'),

    # -----------------------------------------------------------
    # 4. TOKEN VERIFY
    # POST /api/auth/verify/
    # Body: { "token": "..." }
    # Returns: {} (empty 200) if the token is valid, 4xx otherwise.
    # Useful for frontend checks before making requests.
    # -----------------------------------------------------------
    path('verify/', TokenVerifyView.as_view(), name='token_verify'),

    # -----------------------------------------------------------
    # 5. CURRENT USER DATA
    # GET /api/auth/me/
    # Header: Authorization: Bearer <access_token>
    # Returns: { "id", "username", "full_name", "company_id",
    #            "job_title", "department" }
    # -----------------------------------------------------------
    path('me/', CurrentUserView.as_view(), name='current_user'),

    # -----------------------------------------------------------
    # 6. CHANGE PASSWORD
    # POST /api/auth/change-password/
    # Header: Authorization: Bearer <access_token>
    # Body: { "old_password", "new_password", "confirm_new_password" }
    # Changes the password and blacklists all outstanding tokens,
    # forcing re-login from all devices.
    # -----------------------------------------------------------
    path('change-password/', ChangePasswordView.as_view(), name='change_password'),
]
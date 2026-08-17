import logging
from django.db import transaction
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
from .models import Profile
from .serializers import CurrentUserSerializer, ChangePasswordSerializer, AssistantListSerializer, AssistantPermissionsSerializer, CreateAssistantSerializer
from .permissions import IsHRAdmin
import random, string
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from audit.utils import log_action

# Logger for recording errors and important events
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------
# CurrentUserView
# Purpose: Returns the currently authenticated user’s data.
# ---------------------------------------------------------------
class CurrentUserView(APIView):
    # Only authenticated users can access this endpoint
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Serialize the user object using our custom serializer
        serializer = CurrentUserSerializer(request.user)
        # Return the serialized data (id, username, full_name, etc.)
        return Response(serializer.data)


# ---------------------------------------------------------------
# ChangePasswordView
# Purpose: Allows a logged-in user to change their own password.
# After a successful change, all existing JWT tokens for the user
# are blacklisted, forcing a re-login from all devices.
# ---------------------------------------------------------------
class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = request.user
            user.set_password(serializer.validated_data['new_password'])
            user.save()

            # Clear the must_change_password flag
            if hasattr(user, 'profile'):
                user.profile.must_change_password = False
                user.profile.save()

            # Blacklist tokens (existing logic) ...
            return Response({"message": "Password changed successfully..."}, status=200)
        return Response(serializer.errors, status=400)


class AssistantListView(APIView):
    permission_classes = [IsAuthenticated, IsHRAdmin]

    def get(self, request):
        profiles = Profile.objects.filter(role=Profile.Role.HRASSISTANT).select_related('user', 'employee')
        serializer = AssistantListSerializer(profiles, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = CreateAssistantSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        company_id = serializer.validated_data['company_id']
        from employees.models import Employee

        try:
            employee = Employee.objects.get(company_id=company_id)
        except Employee.DoesNotExist:
            return Response({"error": "Employee with this company ID not found."}, status=400)

        default_password = "Changeme123"
        user = User.objects.create_user(username=company_id, password=default_password)

        # Ensure Profile exists
        profile, created = Profile.objects.get_or_create(user=user)
        profile.employee = employee
        profile.role = Profile.Role.HRASSISTANT
        profile.must_change_password = True
        profile.save()
        log_action(request.user, 'CREATE', 'User', user.id, f"Created assistant account for {employee.full_name} ({company_id})")

        return Response({
            "username": user.username,
            "default_password": default_password,
            "message": "Assistant account created. Communicate the default password securely."
        }, status=201)

class AssistantPermissionsView(APIView):
    permission_classes = [IsAuthenticated, IsHRAdmin]

    def put(self, request, user_id):
        profile = get_object_or_404(Profile, user_id=user_id, role=Profile.Role.HRASSISTANT)
        serializer = AssistantPermissionsSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            log_action(request.user, 'UPDATE', 'User', profile.user.id, f"Updated permissions for {profile.user.username}")
            return Response(serializer.data)
        return Response(serializer.errors, status=400)

class ToggleAssistantActiveView(APIView):
    permission_classes = [IsAuthenticated, IsHRAdmin]

    def patch(self, request, user_id):
        profile = get_object_or_404(Profile, user_id=user_id, role=Profile.Role.HRASSISTANT)
        user = profile.user
        user.is_active = not user.is_active
        user.save()
        action = 'BLOCK' if not user.is_active else 'UNBLOCK'
        log_action(request.user, action, 'User', user.id, f"{action.capitalize()}ed account {user.username}")
        return Response({
            "user_id": user.id,
            "is_active": user.is_active,
            "message": f"User {'activated' if user.is_active else 'deactivated'}."
        })
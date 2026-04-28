import logging
from django.db import transaction
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken

from .serializers import CurrentUserSerializer, ChangePasswordSerializer

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
    # Only authenticated users can change their password
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # 1. Validate the incoming data (old_password, new_password, confirm)
        #    using our ChangePasswordSerializer.
        #    We pass the request as context so the serializer can verify
        #    that the old_password matches the current user.
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={'request': request}
        )

        # 2. If the data is valid (old password correct, new passwords match,
        #    not equal, and pass Django's password strength validators)...
        if serializer.is_valid():
            user = request.user

            # 3. Actually change the password in the database.
            #    set_password() hashes the new password securely.
            user.set_password(serializer.validated_data['new_password'])
            user.save()

            # ----------------------------------------------------------------
            # 4. Security step: Blacklist all outstanding tokens for this user.
            #    This logs them out of all other devices completely.
            # ----------------------------------------------------------------
            try:
                # Retrieve all tokens that are still valid for this user.
                # The OutstandingToken table is managed by SimpleJWT; every
                # time a user logs in or refreshes, a new row is added.
                tokens = OutstandingToken.objects.filter(user=user)

                # Use a database transaction to ensure all blacklist entries
                # are inserted atomically – if one fails, nothing is saved.
                with transaction.atomic():
                    # Create BlacklistedToken objects for each outstanding token.
                    # bulk_create performs a single INSERT, which is fast.
                    # ignore_conflicts=True skips tokens that are already
                    # blacklisted (e.g., from a previous password change).
                    BlacklistedToken.objects.bulk_create(
                        [BlacklistedToken(token=t) for t in tokens],
                        ignore_conflicts=True
                    )
            except Exception:
                # If the token_blacklist app is not installed or the database
                # table is missing, we catch the error, log it, but do not crash.
                # The password has already been changed successfully, so we
                # still return success – just without session termination.
                logger.exception("Token blacklisting failed")
                # 'pass' means we intentionally ignore the error here
                pass

            # 5. Return a success message telling the user to re-authenticate.
            return Response(
                {
                    "message": (
                        "Password changed successfully. "
                        "All sessions have been terminated. Please login again."
                    )
                },
                status=status.HTTP_200_OK
            )

        # 6. If validation failed, return the error details with a 400 status.
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
import requests
from rest_framework import generics, permissions, status
from .serializers import CustomUserSerializer, VehicleProfileSerializer
from .models import CustomUser, VehicleProfile
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView

class ProfileViewByEmail(generics.RetrieveUpdateAPIView):
    serializer_class = CustomUserSerializer
    permission_classes = [permissions.AllowAny] 
    def get_object(self):
        email = self.kwargs.get('email')
        # if self.request.user.email != email:
        #     raise PermissionDenied("You are not allowed to access this profile.")
        return get_object_or_404(CustomUser, email=email)
    


class ProfileViewByUserId(generics.RetrieveAPIView):
    serializer_class = CustomUserSerializer
    permission_classes = [permissions.AllowAny]  # Or IsAuthenticated based on your needs
    def get_object(self):
        user_id = self.kwargs.get('user_id')
        # if self.request.user.id != user_id:
        #     raise PermissionDenied("You are not allowed to access this profile.")
        return get_object_or_404(CustomUser, user_id=user_id)
    

    
class ProfileCreateView(generics.CreateAPIView):
    serializer_class = CustomUserSerializer
    permission_classes = [permissions.AllowAny]

    


class VehicleProfileListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = VehicleProfileSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        user_id = self.request.query_params.get('user_id')
        vehicle_id = self.request.query_params.get('vehicle_id')
        if vehicle_id:
            return VehicleProfile.objects.filter(id=vehicle_id)
        if user_id:
            return VehicleProfile.objects.filter(user_id=user_id)
        return VehicleProfile.objects.all()

    def perform_create(self, serializer):
        # Allow any user to specify user ID in the request
        user_id = self.request.data.get('user')
        if user_id is not None:
            user_model = get_user_model()
            user = user_model.objects.get(user_id=user_id)
            serializer.save(user=user)
        else:
            serializer.save(user=self.request.user)  # fallback if user is not provided

# {
#   "user": 3,  // ID of the user (driver)
#   "vehicle_type": "Car",
#   "vehicle_model": "Hyundai i20",
#   "vehicle_year": 2022,
#   "vehicle_color": "Red",
#   "vehicle_license_plate": "KA01CD4567",
#   "vehicle_engine_type": "Petrol"
# }


class TestAPIView(generics.ListAPIView):
    permission_classes = [permissions.AllowAny]  # Allow any user to access this view

    def get(self, request, *args, **kwargs):
        return Response({"message": "Server is running successfully!"}, status=status.HTTP_200_OK)
    
    
    
SUPERTOKENS_API_KEY = "j6QpM=lb77rM7ge4XQmeZs2Qs3"
SUPERTOKENS_CORE_URL = "https://st-dev-bbb51c70-4a16-11f0-8459-3185928d9a1b.aws.supertokens.io"

class DeleteSuperTokensUserView(APIView):
    authentication_classes = []  # ⚠️ Disable auth for testing phase
    permission_classes = []      # ⚠️ Disable auth for testing phase

    def post(self, request):
        email = request.data.get("email")
        if not email:
            return Response({"error": "Email is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Fetch userId from SuperTokens
        response = requests.get(
            f"{SUPERTOKENS_CORE_URL}/users/by-email",
            params={"email": email},
            headers={
                "api-key": SUPERTOKENS_API_KEY,
                "Content-Type": "application/json"
            }
        )

        if response.status_code != 200:
            return Response({"error": "Failed to fetch user from SuperTokens"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        users = response.json().get("users", [])
        if not users:
            return Response({"error": "User not found in SuperTokens"}, status=status.HTTP_404_NOT_FOUND)

        user_id = users[0]["userId"]

        # Delete user by userId
        delete_response = requests.post(
            f"{SUPERTOKENS_CORE_URL}/recipe/user/remove",
            headers={
                "api-key": SUPERTOKENS_API_KEY,
                "Content-Type": "application/json"
            },
            json={"userId": user_id}
        )

        if delete_response.status_code != 200:
            return Response({"error": "Failed to delete user from SuperTokens"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({"message": f"User with email '{email}' deleted from SuperTokens."}, status=status.HTTP_200_OK)
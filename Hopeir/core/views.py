import requests
import supertokens_python
from rest_framework import generics, permissions, status
from .serializers import CustomUserSerializer, VehicleProfileSerializer
from .models import CustomUser, VehicleProfile
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from django.db import transaction
from django.conf import settings
from rest_framework.permissions import AllowAny

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
    
    
    
class DeleteUserByEmailView(APIView):
    """
    FOR TESTING ONLY. Deletes a user by email.
    This endpoint is disabled when settings.DEBUG is False.
    """
    authentication_classes = []
    permission_classes = [AllowAny]
    def delete(self, request):
        # **SECURITY CHECK**: Only allow this function to run in DEBUG mode.
        if not settings.DEBUG:
            return Response({
                "status": "error",
                "message": "This endpoint is for testing only and is disabled in production."
            }, status=status.HTTP_403_FORBIDDEN)

        email = request.data.get('email')

        if not email:
            return Response({
                "status": "error",
                "message": "Email is required in the request body."
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            # A transaction ensures the entire operation is atomic.
            with transaction.atomic():
                # Step 1: Find the user in your local database by their email.
                user_to_delete = CustomUser.objects.get(email=email)
                
                # Step 2: Get their SuperTokens user_id from your local record.
                user_id = user_to_delete.user_id

                # Step 3: Delete the user from the SuperTokens core using their ID.
                supertokens_python.delete_user(user_id)
                
                # Step 4: Delete the user from your local Django database.
                # This will also cascade and delete related VehicleProfile, etc.
                user_to_delete.delete()

            return Response({
                "status": "success",
                "message": f"User with email '{email}' deleted successfully."
            }, status=status.HTTP_200_OK)

        except CustomUser.DoesNotExist:
            return Response({
                "status": "error",
                "message": f"User with email '{email}' not found."
            }, status=status.HTTP_404_NOT_FOUND)
            
        except Exception as e:
            return Response({
                "status": "error",
                "message": f"An unexpected error occurred: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
from rest_framework import generics, permissions, status
from .serializers import CustomUserSerializer, VehicleProfileSerializer
from .models import CustomUser, VehicleProfile
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied
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


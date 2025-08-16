import supertokens_python
from django.db import transaction
from jsonschema import ValidationError
from rest_framework import generics, permissions, status
from .serializers import CustomUserSerializer, VehicleProfileSerializer
from .models import CustomUser, VehicleProfile
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from django.conf import settings
from rest_framework.permissions import AllowAny
from asgiref.sync import async_to_sync
from supertokens_python.asyncio import delete_user

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
    

    
class ProfileCreateView(generics.RetrieveUpdateAPIView):
    serializer_class = CustomUserSerializer
    permission_classes = [permissions.AllowAny] # Allow any request for testing

    def get_object(self):
        queryset = CustomUser.objects.all()
        email = self.request.data.get('email')
        
        if not email:
            raise ValidationError({'email': 'Email must be provided in the request body.'})
        obj = get_object_or_404(queryset, email=email)
        return obj

    


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
    FOR TESTING ONLY. Deletes a user from both SuperTokens
    and the local Django DB using their email.
    """
    authentication_classes = []
    permission_classes = [AllowAny]

    # 👇 2. Change the method back to a synchronous 'def'
    def delete(self, request):
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
            with transaction.atomic():
                # Database calls can now be synchronous again
                user_to_delete = CustomUser.objects.get(email=email)
                user_id = user_to_delete.user_id

                # 👇 3. Wrap the async delete_user call in async_to_sync
                async_to_sync(delete_user)(user_id)
                
                # This database call is also synchronous
                user_to_delete.delete()

            return Response({
                "status": "success",
                "message": f"User with email '{email}' deleted successfully from SuperTokens and the local DB."
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

from rest_framework import generics, permissions
from .serializers import CustomUserSerializer, VehicleProfileSerializer
from .models import CustomUser, VehicleProfile
from rest_framework.response import Response
from django.contrib.auth import get_user_model

# class SyncSupertokensUserView(GenericAPIView):
#     permission_classes = [permissions.IsAuthenticated]

#     def post(self, request):
#         user_id = get_user_id(request)

#         if not user_id:
#             return Response({"error": "Invalid session"}, status=401)

#         email = request.data.get("email")

#         if not email:
#             return Response({"error": "Email is required"}, status=400)

#         user, created = CustomUser.objects.get_or_create(
#             email=email,
#             defaults={
#                 "username": email.split("@")[0],  # fallback
#                 "first_name": "",
#                 "last_name": "",
#             }
#         )

#         return Response({
#             "status": "OK",
#             "user_id": user.user_id,
#             "created": created
#         })

class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = CustomUserSerializer
    permission_classes = [permissions.IsAuthenticated] 
    def get_object(self):
        return self.request.user


class VehicleProfileListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = VehicleProfileSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        user_id = self.request.query_params.get('user_id')
        if user_id:
            return VehicleProfile.objects.filter(user__id=user_id)
        return VehicleProfile.objects.all()

    def perform_create(self, serializer):
        # Allow any user to specify user ID in the request
        user_id = self.request.data.get('user')
        if user_id is not None:
            user_model = get_user_model()
            user = user_model.objects.get(id=user_id)
            serializer.save(user=user)
        else:
            serializer.save(user=self.request.user)  # fallback if user is not provided

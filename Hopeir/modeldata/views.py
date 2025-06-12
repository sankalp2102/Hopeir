from django.shortcuts import render
from rest_framework import generics, permissions
from .models import RideInput
from .serializers import RideInputSerializer
# Create your views here.

class RideInputCreateView(generics.CreateAPIView):
    serializer_class = RideInputSerializer
    permission_classes = [permissions.AllowAny]  # Use IsAuthenticated if using login

    def perform_create(self, serializer):
        user = self.request.data.get('user')  # Accept user ID explicitly in body
        if user:
            serializer.save(user_id=user)
        else:
            serializer.save()

# GET: ML model can fetch all route data
class RideInputListView(generics.ListAPIView):
    queryset = RideInput.objects.all()
    serializer_class = RideInputSerializer
    permission_classes = [permissions.AllowAny]
from django.shortcuts import render
from rest_framework import generics, permissions
from .models import Fare
from .serializers import FareSerializer
# Create your views here.

class FareView(generics.ListCreateAPIView):
    queryset = Fare.objects.all()
    serializer_class = FareSerializer
    permission_classes = [permissions.AllowAny]
    
    
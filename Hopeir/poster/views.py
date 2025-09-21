from django.shortcuts import render
from rest_framework import generics
from .models import Poster
from .serializers import PosterSerializer
from rest_framework.permissions import AllowAny



class PosterListCreateView(generics.ListCreateAPIView):
    serializer_class = PosterSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        return Poster.objects.filter(is_active=True).order_by('-created_at')
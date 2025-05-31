from django.shortcuts import render
from rest_framework import generics, permissions
from .models import Station
from .serializers import StationsSerializer
# Create your views here.

class StationView(generics.ListCreateAPIView):
    queryset = Station.objects.all()
    serializer_class = StationsSerializer
    permission_classes = [permissions.AllowAny]
    
# {
#     "name": "Dublin City Centre Station",
#     "latitude": 53.349805,
#     "longitude": -6.26031,
#     "address": "O'Connell Street, Dublin 1",
#     "sector": "City Centre",
#     "city": "Dublin",
#     "country": "Ireland",
#     "postal_code": "D01",
#     "landmark": "Near Spire of Dublin"
#   },
from django.shortcuts import render
from rest_framework import generics, permissions
from .models import Station
from .serializers import StationsSerializer
# Create your views here.

class StationCreateView(generics.CreateAPIView):
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

class StationListView(generics.ListAPIView):
    serializer_class = StationsSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        station_id = self.request.query_params.get('station_id')
        if station_id:
            return Station.objects.filter(id=station_id)
        return Station.objects.all()
    

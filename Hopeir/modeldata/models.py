from django.db import models
from core.models import CustomUser
# Create your models here.

class RideInput(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='ride_inputs')
    starting = models.CharField(max_length=255, null=True, blank=True)
    destination = models.CharField(max_length=255)
    preferred_route = models.TextField(null=True, blank=True)
    choice =models.CharField(null=True, blank=True, max_length=255)
    travel_time = models.TimeField(null=True, blank=True)  # optional
    frequency = models.PositiveIntegerField(null=True, blank=True)  # number of rides per week
    
    def __str__(self):
        return f"Ride Input by {self.user.email} to {self.destination} with frequency {self.frequency}"
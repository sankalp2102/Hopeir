from django.db import models
from core.models import VehicleProfile, CustomUser
from stations.models import Station
from fare.models import Fare

class Rides(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='rides')
    vehicle = models.ForeignKey(VehicleProfile, on_delete=models.CASCADE, related_name='rides')
    start_location = models.ForeignKey(Station, on_delete=models.CASCADE, related_name='rides_start', null=True, blank=True)
    end_location = models.ForeignKey(Station, on_delete=models.CASCADE, related_name='rides_end', null=True, blank=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    distance = models.FloatField(null=True, blank=True)  # in kilometers
    fare = models.ForeignKey(Fare, on_delete=models.SET_NULL, null=True, blank=True, related_name='rides')
    status = models.CharField(max_length=50, default='pending')  # e.g., pending, completed, cancelled
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Ride {self.id} by {self.user.email} from {self.start_location} to {self.end_location}"

class RideFeedback(models.Model):
    ride = models.ForeignKey(Rides, on_delete=models.CASCADE, related_name='feedback')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='ride_feedback')
    rating = models.IntegerField()  # e.g., 1 to 5 stars
    comment = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Feedback for Ride {self.ride.id} by {self.user.email}"
    

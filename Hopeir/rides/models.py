from django.db import models
from core.models import VehicleProfile, CustomUser
from stations.models import Station
from fare.models import Fare

class Rides(models.Model):
    STATUS_CHOICES = [
    ('pending', 'Pending'),
    # ('accepted', 'Accepted'),
    ('ongoing', 'Ongoing'),
    ('completed', 'Completed'),
    ('cancelled', 'Cancelled'),
]
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='rides')
    vehicle = models.ForeignKey(VehicleProfile, on_delete=models.CASCADE, related_name='rides')
    start_location = models.ForeignKey(Station, on_delete=models.CASCADE, related_name='rides_start', null=True, blank=True)
    end_location = models.ForeignKey(Station, on_delete=models.CASCADE, related_name='rides_end', null=True, blank=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    distance = models.FloatField(null=True, blank=True)  # in kilometers
    fare = models.ForeignKey(Fare, on_delete=models.SET_NULL, null=True, blank=True, related_name='rides')
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='pending')  # e.g., pending, completed, cancelled
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    seats = models.IntegerField(default=1, null=True, blank=True)

    def __str__(self):
        return f"Ride {self.id} by {self.user.email} from {self.start_location} to {self.end_location}"

class RideRequest(models.Model):
    ride = models.ForeignKey(Rides, on_delete=models.CASCADE, related_name='ride_requests')
    from_user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='ride_requests', null=True, blank=True)
    request_status = models.CharField(max_length=20, choices=[('pending', 'Pending'), ('accepted', 'Accepted'), ('rejected', 'Rejected')], default='pending')
    requested_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Ride {self.ride.id} ({self.request_status} and request id is {self.id} and send by {self.from_user.email}) and driver is {self.ride.user.email}"
    

class RideFeedback(models.Model):
    ride = models.ForeignKey(Rides, on_delete=models.CASCADE, related_name='feedback')
    from_user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='feedback_given',  null=True, blank=True)
    to_user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='feedback_received',  null=True, blank=True)
    rating = models.PositiveIntegerField(null=True, blank=True)
    comment = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Feedback for Ride id {self.ride.id} ,feedback id is {self.id}"
    
    

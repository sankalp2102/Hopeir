from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here.

USER_ROLES = (
    ('User', 'user'),
    ('Admin', 'admin'),
)

class CustomUser(AbstractUser):
    user_id = models.AutoField(primary_key=True)
    phone_number = models.CharField(max_length=15, unique=True, null=True)
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=30, null=True, blank=True)
    last_name = models.CharField(max_length=30, null=True, blank=True)
    bio = models.TextField(null = True, blank=True)
    role = models.CharField(max_length=10, choices=USER_ROLES, default='User')
    date_of_birth = models.DateField(null=True, blank=True)
    profile_picture = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.email} {self.user_id}"

class VehicleProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    vehicle_type = models.CharField(max_length=255)
    vehicle_model = models.CharField(max_length=255)
    vehicle_year = models.IntegerField()
    vehicle_color = models.CharField(max_length=255)
    vehicle_license_plate = models.CharField(max_length=255)
    vehicle_engine_type = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.vehicle_type} {self.vehicle_model} {self.vehicle_year}"

class VehicleLocation(models.Model):
    vehicle = models.ForeignKey(VehicleProfile, on_delete=models.CASCADE)
    latitude = models.FloatField()
    longitude = models.FloatField()
    
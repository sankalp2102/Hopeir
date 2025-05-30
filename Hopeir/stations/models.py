from django.db import models

# Create your models here.

class Station(models.Model):
    name = models.CharField(max_length=255, unique=True)
    latitude = models.FloatField()
    longitude = models.FloatField()
    address = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    sector = models.CharField(max_length=50, null=True, blank=True)
    city = models.CharField(max_length=50, null=True, blank=True)
    country = models.CharField(max_length=50, null=True, blank=True)
    postal_code = models.CharField(max_length=20, null=True, blank=True)
    landmark = models.CharField(max_length=255, null=True, blank=True)
    
    
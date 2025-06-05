from django.contrib import admin
from . models import Rides, RiderFeedback, RideRequest
# Register your models here.

admin.site.register(Rides)
admin.site.register(RiderFeedback)
admin.site.register(RideRequest)
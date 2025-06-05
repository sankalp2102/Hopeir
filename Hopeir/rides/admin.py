from django.contrib import admin
from . models import Rides, RideFeedback, RideRequest
# Register your models here.

admin.site.register(Rides)
admin.site.register(RideRequest)
admin.site.register(RideFeedback)
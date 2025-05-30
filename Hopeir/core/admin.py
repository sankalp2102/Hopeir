from django.contrib import admin
from .models import CustomUser, VehicleProfile

# Register your models here.
admin.site.register(CustomUser)
admin.site.register(VehicleProfile)

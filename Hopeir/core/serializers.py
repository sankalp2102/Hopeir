from rest_framework import serializers
from .models import CustomUser, VehicleProfile

class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = '__all__'
        read_only_fields = ['user_id', 'email', 'role', 'created_at', 'updated_at']

class VehicleProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = VehicleProfile
        fields = ['id', 'user', 'vehicle_type', 'vehicle_model', 'vehicle_year', 'vehicle_color', 'vehicle_license_plate', 'vehicle_engine_type']
        read_only_fields = ["id", "created_at", "updated_at"]
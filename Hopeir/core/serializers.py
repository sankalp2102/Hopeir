from rest_framework import serializers
from .models import CustomUser, VehicleProfile

class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = [
            'user_id', 'email', 'first_name', 'last_name', 'phone_number', 
            'bio', 'role', 'date_of_birth', 'profile_picture', 'created_at'
        ]
        
    
    def validate_email(self, value):
        email = value.strip().lower()
        if CustomUser.objects.filter(email=email).exists():
            raise serializers.ValidationError("This email is already registered.")
        return email
    
        
    def create(self, validated_data):
        email = validated_data.get("email")
        password = validated_data.pop("password", None)

        if CustomUser.objects.filter(email=email).exists():
            raise serializers.ValidationError({"email": "This email is already registered."})

        user = CustomUser(**validated_data)
        if password:
            user.set_password(password)  # Hash the password correctly
        user.save()
        return user
    
    
class VehicleProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = VehicleProfile
        fields = ['id', 'user', 'vehicle_type', 'vehicle_model', 'vehicle_year', 'vehicle_color', 'vehicle_license_plate', 'vehicle_engine_type']
        read_only_fields = ["id", "created_at", "updated_at"]
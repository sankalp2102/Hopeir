from rest_framework import serializers
from .models import RideInput

class RideInputSerializer(serializers.ModelSerializer):
    class Meta:
        model = RideInput
        fields = '__all__'
        read_only_fields = ['user']  # Assuming user is set automatically, e.g., from request.user in the view
        

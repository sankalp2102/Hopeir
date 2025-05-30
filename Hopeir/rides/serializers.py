from rest_framework import serializers
from .models import Rides

class RidesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rides
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']
        
        
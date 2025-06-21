from rest_framework import serializers
from .models import Rides, RideRequest, RideFeedback

class RidesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rides
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']
        

class RideRequestCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = RideRequest
        fields = ['ride', 'from_user']

    def validate(self, attrs):
        ride = attrs['ride']
        if ride.seats <= 0:
            raise serializers.ValidationError("No seats available.")
        return attrs


class RideRequestListSerializer(serializers.ModelSerializer):
    passenger_name = serializers.CharField(source='from_user.first_name', read_only=True)
    ride_id = serializers.IntegerField(source='ride.id', read_only=True)

    class Meta:
        model = RideRequest
        fields = ['id', 'ride_id', 'passenger_name', 'requested_at', 'from_user', 'request_status']


class RideRequestUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = RideRequest
        fields = ['status']

    def validate(self, attrs):
        # if attrs['status'] not in ['accepted', 'rejected']:
        #     raise serializers.ValidationError("Invalid status.")
        return attrs


class RideFeedbackSerializer(serializers.ModelSerializer):
    
    

    class Meta:
        model = RideFeedback
        fields = '__all__'
        read_only_fields = ['id', 'created_at']

    # def validate(self, data):
    #     if data['from_user'] == data['to_user']:
    #         raise serializers.ValidationError("You cannot give feedback to yourself.")
    #     return data
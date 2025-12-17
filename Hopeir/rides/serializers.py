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
        from_user = attrs['from_user']

        if RideRequest.objects.filter(
            ride=ride,
            from_user=from_user
        ).exists():
            raise serializers.ValidationError(
                "You have already requested this ride"
            )

        if ride.seats <= 0:
            raise serializers.ValidationError("No seats available")

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
        fields = ['request_status']

    def validate(self, attrs):
        if attrs['request_status'] not in ['accepted', 'rejected']:
            raise serializers.ValidationError("Invalid request status")
        return attrs


class RideFeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = RideFeedback
        fields = '__all__'
        read_only_fields = ['id', 'created_at']

    def validate(self, data):
        if data['from_user'] == data['to_user']:
            raise serializers.ValidationError(
                "You cannot give feedback to yourself"
            )
        return data

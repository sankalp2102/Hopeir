from rest_framework import serializers
from .models import Rides, RideRequest, RiderFeedback, PassangerFeedback

class RidesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rides
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']
        


class RideRequestCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = RideRequest
        fields = ['ride']

    def validate(self, attrs):
        # user = self.context['request'].user
        # ride = attrs['ride']

        # if ride.user == user:
        #     raise serializers.ValidationError("You cannot request your own ride.")

        # if RideRequest.objects.filter(ride=ride, passenger=user).exists():
        #     raise serializers.ValidationError("You have already requested this ride.")

        return attrs

    def create(self, validated_data):
        # validated_data['passenger'] = self.context['request'].user
        return super().create(validated_data)


class RideRequestUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = RideRequest
        fields = ['status']

    def validate(self, attrs):
        # if attrs['status'] not in ['accepted', 'rejected']:
        #     raise serializers.ValidationError("Invalid status.")
        return attrs


class RiderFeedbackSerializer(serializers.ModelSerializer):
    class meta:
        model = RiderFeedback
        fields = "__all__"
        
class PassangerFeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = PassangerFeedback
        fields = "__all__"


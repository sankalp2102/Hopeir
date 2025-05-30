from django.shortcuts import render
from rest_framework.generics import GenericAPIView
from rest_framework import mixins, status
from rest_framework.response import Response
from .models import Rides
from .serializers import RidesSerializer
from django.utils.timezone import now

class RideCreateView(mixins.CreateModelMixin, GenericAPIView):
    queryset = Rides.objects.all()
    serializer_class = RidesSerializer

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)


# {
#   "user": 1,
#   "vehicle": 2,
#   "start_location": 1,
#   "end_location": 2,
#   "start_time": "2025-06-01T10:00:00Z",
#   "end_time": "2025-06-01T10:30:00Z",
#   "distance": 10.5,
#   "fare": 1,
#   "status": "pending"
# }



class RideActionView(GenericAPIView):
    queryset = Rides.objects.all()
    serializer_class = RidesSerializer  # Optional; only used if you want to return serialized ride

    def post(self, request, *args, **kwargs):
        ride_id = kwargs.get('ride_id')
        action = kwargs.get('action')

        try:
            ride = self.get_queryset().get(pk=ride_id)
        except Rides.DoesNotExist:
            return Response({"error": "Ride not found"}, status=status.HTTP_404_NOT_FOUND)

        # Handle actions
        if action == "start":
            if ride.status != "pending":
                return Response({"error": "Ride cannot be started"}, status=status.HTTP_400_BAD_REQUEST)
            ride.status = "ongoing"
            ride.start_time = now()
        elif action == "end":
            if ride.status != "ongoing":
                return Response({"error": "Ride cannot be ended"}, status=status.HTTP_400_BAD_REQUEST)
            ride.status = "completed"
            ride.end_time = now()
        elif action == "cancel":
            if ride.status not in ["pending", "ongoing"]:
                return Response({"error": "Ride cannot be cancelled"}, status=status.HTTP_400_BAD_REQUEST)
            ride.status = "cancelled"
        else:
            return Response({"error": "Invalid action"}, status=status.HTTP_400_BAD_REQUEST)

        ride.save()

        # Optionally return updated ride data
        serializer = self.get_serializer(ride)
        return Response({
            "message": f"Ride {action}ed successfully",
            "ride": serializer.data
        }, status=status.HTTP_200_OK)


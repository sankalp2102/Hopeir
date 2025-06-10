from django.shortcuts import render
from rest_framework.generics import GenericAPIView
from rest_framework import mixins, status, generics
from rest_framework.response import Response
from .models import Rides, RideRequest, RideFeedback
from .serializers import (RidesSerializer, RideRequestCreateSerializer, 
                          RideRequestUpdateSerializer, RideFeedbackSerializer,
                          RideRequestListSerializer)
from django.utils.timezone import now
from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied

class RideCreateView(mixins.CreateModelMixin, GenericAPIView):
    queryset = Rides.objects.all()
    serializer_class = RidesSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)
    
class RideListView(generics.ListAPIView):
    serializer_class = RidesSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        queryset = Rides.objects.all()
        user_id = self.request.query_params.get('user_id')

        if user_id:
            queryset = queryset.filter(user_id=user_id)

        return queryset


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
    serializer_class = RidesSerializer
    permission_classes = [permissions.AllowAny]  # change to IsAuthenticated if needed

    def post(self, request, ride_id, action, *args, **kwargs):
        try:
            ride = self.get_queryset().get(pk=ride_id)
        except Rides.DoesNotExist:
            return Response({"error": "Ride not found"}, status=status.HTTP_404_NOT_FOUND)

        # Action Handling
        if action == "start":
            if ride.status not in ["pending", "accepted"]:
                return Response({"error": "Ride cannot be started in current state"}, status=400)
            ride.status = "ongoing"
            ride.start_time = now()

        elif action == "end":
            if ride.status != "ongoing":
                return Response({"error": "Ride cannot be ended unless it is ongoing"}, status=400)
            ride.status = "completed"
            ride.end_time = now()

        elif action == "cancel":
            if ride.status in ["completed", "cancelled"]:
                return Response({"error": "Ride is already completed or cancelled"}, status=400)
            ride.status = "cancelled"

        else:
            return Response({"error": "Invalid action"}, status=400)

        ride.save()

        return Response({
            "message": f"Ride {action}ed successfully",
            "ride": self.get_serializer(ride).data
        }, status=200)



class RideRequestCreateView(generics.CreateAPIView):
    queryset = RideRequest.objects.all()
    serializer_class = RideRequestCreateSerializer
    permission_classes = [permissions.AllowAny]  # use IsAuthenticated later

    def get_serializer_context(self):
        return super().get_serializer_context()
    
# {
#   "ride": 1,
#   "from_user": 1
# }


class RideRequestListForDriverView(generics.ListAPIView):
    serializer_class = RideRequestListSerializer
    permission_classes = [permissions.AllowAny]  # allow unauthenticated for testing

    def get_queryset(self):
        user_id = self.request.query_params.get('user_id')
        if not user_id:
            return RideRequest.objects.none()

        return RideRequest.objects.filter(ride__user__user_id=user_id)
    


class RideRequestRespondView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]  # Change to IsAuthenticated in production
    serializer_class = None  # No serializer needed here, we handle data manually

    def post(self, request, pk):
        action = request.data.get('action')
        user_id = request.data.get('user_id')

        if not user_id:
            return Response({"error": "user_id is required for testing."}, status=status.HTTP_400_BAD_REQUEST)

        # Fetch the RideRequest object only if it belongs to the driver's ride
        try:
            ride_request = RideRequest.objects.get(id=pk, ride__user__user_id=user_id)
        except RideRequest.DoesNotExist:
            return Response({"error": "Ride request not found or unauthorized."}, status=status.HTTP_404_NOT_FOUND)

        if ride_request.status != 'pending':
            return Response({"error": "This request has already been responded to."}, status=status.HTTP_400_BAD_REQUEST)

        if action == 'accept':
            if ride_request.ride.seats <= 0:
                return Response({"error": "No seats available."}, status=status.HTTP_400_BAD_REQUEST)
            ride_request.status = 'accepted'
            ride_request.ride.seats -= 1
            ride_request.ride.save()
        elif action == 'reject':
            ride_request.status = 'rejected'
        else:
            return Response({"error": "Invalid action."}, status=status.HTTP_400_BAD_REQUEST)

        ride_request.save()
        return Response({"message": f"Request {action}ed successfully."}, status=status.HTTP_200_OK)
    
# {
#   "action": "accept",
#   "driver_id": 2
# }


class RideFeedbackCreateView(generics.CreateAPIView):
    serializer_class = RideFeedbackSerializer
    permission_classes = [permissions.AllowAny]  # or IsAuthenticated if needed

    def perform_create(self, serializer):
        serializer.save()
    

class RideFeedbackListView(generics.ListAPIView):
    serializer_class = RideFeedbackSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        queryset = RideFeedback.objects.all()

        ride_id = self.request.query_params.get('ride_id')
        from_user_id = self.request.query_params.get('from_user')
        to_user_id = self.request.query_params.get('to_user')

        if ride_id:
            queryset = queryset.filter(ride_id=ride_id)

        if from_user_id:
            queryset = queryset.filter(from_user_id=from_user_id)

        if to_user_id:
            queryset = queryset.filter(to_user_id=to_user_id)

        return queryset
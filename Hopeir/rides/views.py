from rest_framework.views import APIView
from rest_framework.generics import GenericAPIView
from rest_framework import mixins, status, generics
from rest_framework.response import Response
from .models import Rides, RideRequest, RideFeedback
from .serializers import (RidesSerializer, RideRequestCreateSerializer, 
                          RideFeedbackSerializer, RideRequestListSerializer)
from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied
from django.db.models import Q
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
channel_layer = get_channel_layer()


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
        ride_id = self.request.query_params.get('ride_id')

        if user_id:
            queryset = queryset.filter(user_id=user_id)
        if ride_id:
            queryset = queryset.filter(id=ride_id)

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



# class RideActionView(GenericAPIView):
#     queryset = Rides.objects.all()
#     serializer_class = RidesSerializer
#     permission_classes = [permissions.AllowAny]  # OPEN FOR TESTING

#     def post(self, request, ride_id, action, *args, **kwargs):
#         try:
#             ride = self.get_queryset().get(pk=ride_id)
#         except Rides.DoesNotExist:
#             return Response({"error": "Ride not found"}, status=404)

#         # Block changes if already completed or cancelled
#         if ride.status in ["completed", "cancelled"]:
#             return Response({"error": f"Ride is already {ride.status} and cannot be changed"}, status=400)

#         # Basic RideRequest existence check for test phase (not enforcing specific user)
#         if not RideRequest.objects.filter(ride=ride).exists():
#             return Response({"error": "No ride request found for this ride"}, status=403)

#         # Handle valid actions
#         if action == "start":
#             ride.status = "ongoing"
#             ride.start_time = now()
#             RideRequest.objects.filter(ride=ride, status="pending").update(status="rejected")

#         elif action == "end":
#             if ride.status != "ongoing":
#                 return Response({"error": "Ride cannot be ended unless it is ongoing"}, status=400)
#             ride.status = "completed"
#             ride.end_time = now()

#         elif action == "cancel":
#             ride.status = "cancelled"

#         else:
#             return Response({"error": "Invalid action"}, status=400)

#         ride.save()

#         return Response({
#             "message": f"Ride {action}ed successfully",
#             "ride": self.get_serializer(ride).data
#         }, status=200)
        

        





class RideRequestCreateView(generics.CreateAPIView):
    queryset = RideRequest.objects.all()
    serializer_class = RideRequestCreateSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ride_request = serializer.save()

        # Send WebSocket event
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            "ride_requests",
            {
                "type": "ride_request_notification",
                "payload": {
                    "event": "request_created",
                    "ride_id": ride_request.ride.id,
                    "request_id": ride_request.id,
                    "status": ride_request.status,
                    "from_user": ride_request.from_user.id,
                }
            }
        )

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    
# {
#   "ride": 1,
#   "from_user": 1
# }


class RideRequestRespondView(APIView):
    def post(self, request, request_id):
        try:
            ride_request = RideRequest.objects.get(id=request_id)
        except RideRequest.DoesNotExist:
            return Response({"error": "Ride request not found"}, status=404)

        status_value = request.data.get("status")
        if status_value not in ["accepted", "rejected"]:
            return Response({"error": "Invalid status. Must be 'accepted' or 'rejected'"}, status=400)

        ride_request.status = status_value
        ride_request.save()

        # Send WebSocket update
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            "ride_requests",
            {
                "type": "ride_request_notification",
                "payload": {
                    "event": "request_responded",
                    "ride_id": ride_request.ride.id,
                    "request_id": ride_request.id,
                    "status": ride_request.status,
                    "from_user": ride_request.from_user.id,
                }
            }
        )

        return Response({"success": True, "status": ride_request.status})




class RideRequestListForDriverView(generics.ListAPIView):
    serializer_class = RideRequestListSerializer
    permission_classes = [permissions.AllowAny]  # allow unauthenticated for testing

    def get_queryset(self):
        user_id = self.request.query_params.get('user_id')
        if not user_id:
            return RideRequest.objects.none()

        try:
            user_id = int(user_id)  # Ensure it's an integer
        except ValueError:
            return RideRequest.objects.none()

        return RideRequest.objects.filter(
            Q(from_user__user_id=user_id) | Q(ride__user__user_id=user_id)
        ).distinct()
    

    
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
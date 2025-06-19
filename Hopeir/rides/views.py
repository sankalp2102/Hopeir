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
from .utils import notify_ride_update, notify_user_about_request
from datetime import datetime
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
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ride_request = serializer.save()

        request_data = {
            'request_id': ride_request.id,
            'ride_id': ride_request.ride.id,
            'from_user': {
                'id': ride_request.from_user.user_id,
                'name': ride_request.from_user.first_name
            },
            'request_status': 'pending',
            'requested_at': str(ride_request.requested_at)
        }

        # Notify the driver
        notify_user_about_request(
            user_id=ride_request.ride.user.user_id,
            request_data=request_data,
            notification_type='created'
        )

        return Response({
            "success": True,
            "message": "Ride request created",
            "data": request_data
        }, status=request_status.HTTP_201_CREATED)

    
# {
#   "ride": 1,
#   "from_user": 1
# }


class RideRequestRespondView(generics.UpdateAPIView):
    queryset = RideRequest.objects.all()
    serializer_class = RideRequestCreateSerializer
    permission_classes = [permissions.AllowAny]

    def update(self, request, *args, **kwargs):
        ride_request = self.get_object()
        new_status = request.data.get("request_status")  # also rename key here

        if new_status not in ["accepted", "rejected"]:
            return Response(
                {"error": "Invalid status. Must be 'accepted' or 'rejected'"},
                status=status.HTTP_400_BAD_REQUEST
            )

        ride_request.request_status = new_status
        ride_request.save()

        response_data = {
            'request_id': ride_request.id,
            'ride_id': ride_request.ride.id,
            'request_status': ride_request.request_status,
            'responded_at': str(datetime.now())
        }

        notify_user_about_request(
            user_id=ride_request.from_user.user_id,
            request_data=response_data,
            notification_type='updated'
        )

        if ride_request.request_status == 'accepted':
            ride = ride_request.ride
            ride.status = 'accepted'
            ride.save()

            notify_ride_update(
                ride_id=ride.id,
                status=ride.status,
                message='Ride request accepted'
            )

        return Response({
            "success": True,
            "message": f"Request {new_status} successfully",
            "data": response_data
        }, status=status.HTTP_200_OK)




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
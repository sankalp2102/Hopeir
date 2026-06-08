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
from .geo_utils import haversine, nearest_point_index_on_path, min_dist_to_path
from datetime import datetime, timezone, timedelta
from stations.models import Station
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
        queryset = Rides.objects.select_related("user", "vehicle")

        user_id = self.request.query_params.get('user_id')
        ride_id = self.request.query_params.get('ride_id')

        if user_id:
            queryset = queryset.filter(user__user_id=user_id)

        if ride_id:
            queryset = queryset.filter(id=ride_id)
        return queryset


# class RideActionView — moved to WebSocket (RideActionConsumer)


class RideRequestCreateView(generics.CreateAPIView):
    queryset = RideRequest.objects.all()
    serializer_class = RideRequestCreateSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        ride = serializer.validated_data['ride']
        from_user = serializer.validated_data['from_user']

        if ride.user == from_user:
            return Response(
                {"error": "You cannot request your own ride"},
                status=status.HTTP_400_BAD_REQUEST
            )

        ride_request = serializer.save()

        request_data = {
            'request_id': ride_request.id,
            'ride_id': ride_request.ride.id,
            # FIX 1: driver_id was missing — frontend had no way to know
            # who the driver is from this response
            'driver_id': str(ride_request.ride.user.user_id),
            'from_user': {
                'id': str(ride_request.from_user.user_id),
                'name': ride_request.from_user.first_name
            },
            'request_status': 'pending',
            'requested_at': str(ride_request.requested_at)
        }

        notify_user_about_request(
            user_id=ride_request.ride.user.user_id,
            request_data=request_data,
            notification_type='created'
        )

        return Response({
            "success": True,
            "message": "Ride request created",
            "data": request_data
        }, status=status.HTTP_201_CREATED)


# class RideRequestRespondView — moved to WebSocket (RideRequestConsumer)


class RideRequestListForDriverView(generics.ListAPIView):
    serializer_class = RideRequestListSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        user_id = self.request.query_params.get('user_id')
        if not user_id:
            return RideRequest.objects.none()

        return RideRequest.objects.filter(
            Q(from_user__user_id=user_id) |
            Q(ride__user__user_id=user_id)
        ).select_related("from_user", "ride", "ride__user").distinct()


class RideFeedbackCreateView(generics.CreateAPIView):
    serializer_class = RideFeedbackSerializer
    permission_classes = [permissions.AllowAny]

    def perform_create(self, serializer):
        serializer.save()


class RideFeedbackListView(generics.ListAPIView):
    serializer_class = RideFeedbackSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        queryset = RideFeedback.objects.select_related("ride", "from_user", "to_user")

        ride_id = self.request.query_params.get('ride_id')
        from_user_id = self.request.query_params.get('from_user_id')
        to_user_id = self.request.query_params.get('to_user_id')

        if ride_id:
            queryset = queryset.filter(ride_id=ride_id)
        if from_user_id:
            queryset = queryset.filter(from_user__user_id=from_user_id)
        if to_user_id:
            queryset = queryset.filter(to_user__user_id=to_user_id)

        return queryset


# ---------------------------------------------------------------------------
# RIDE MATCHING
# ---------------------------------------------------------------------------
STATION_MATCH_RADIUS_KM = 3.0
ROUTE_STATION_RADIUS_KM = 1.0

SCORE_BOTH_EXACT      = 100
SCORE_SAME_START_ONLY = 85
SCORE_SAME_END_ONLY   = 80
SCORE_BOTH_ON_ROUTE   = 65
SCORE_ONE_ON_ROUTE    = 40
SCORE_TIME_BONUS      = 10


class RideMatchView(generics.ListAPIView):
    """
    GET /rides/match/
    Query params:
      rider_start_station_id  (required)
      rider_end_station_id    (required)
      rider_user_id           (required)
      time_window_minutes     (optional)
    """
    serializer_class = RidesSerializer
    permission_classes = [permissions.AllowAny]

    def list(self, request, *args, **kwargs):
        rider_start_id = request.query_params.get('rider_start_station_id')
        rider_end_id   = request.query_params.get('rider_end_station_id')
        rider_user_id  = request.query_params.get('rider_user_id')
        time_window    = request.query_params.get('time_window_minutes')

        if not rider_start_id or not rider_end_id or not rider_user_id:
            return Response(
                {"error": "rider_start_station_id, rider_end_station_id and rider_user_id are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            rider_start = Station.objects.get(id=rider_start_id)
            rider_end   = Station.objects.get(id=rider_end_id)
        except Station.DoesNotExist:
            return Response(
                {"error": "One or both station IDs are invalid."},
                status=status.HTTP_400_BAD_REQUEST
            )

        rides = (
            Rides.objects
            .filter(status='pending', seats__gt=0)
            .exclude(user__user_id=rider_user_id)
            .exclude(ride_requests__from_user__user_id=rider_user_id)
            .select_related('start_location', 'end_location', 'user', 'vehicle')
            .distinct()
        )

        if time_window:
            try:
                window = int(time_window)
                now = datetime.now(tz=timezone.utc)
                rides = rides.filter(
                    start_time__gte=now - timedelta(minutes=window),
                    start_time__lte=now + timedelta(minutes=window),
                )
            except ValueError:
                return Response(
                    {"error": "time_window_minutes must be an integer."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        results = []

        for ride in rides:
            if not ride.start_location or not ride.end_location:
                continue

            driver_start = ride.start_location
            driver_end   = ride.end_location
            path         = ride.route_path or []

            score      = None
            match_zone = None

            exact_start = (rider_start.id == driver_start.id)
            exact_end   = (rider_end.id == driver_end.id)

            # Case 1: perfect match
            if exact_start and exact_end:
                score      = SCORE_BOTH_EXACT
                match_zone = 'exact'

            # Case 2: same start, rider end somewhere on route
            elif exact_start and path:
                dist_rider_end, idx_rider_end = nearest_point_index_on_path(
                    rider_end.latitude, rider_end.longitude, path
                )
                if dist_rider_end <= ROUTE_STATION_RADIUS_KM:
                    _, idx_driver_end = nearest_point_index_on_path(
                        driver_end.latitude, driver_end.longitude, path
                    )
                    if idx_rider_end <= idx_driver_end:
                        score      = SCORE_SAME_START_ONLY
                        match_zone = 'same_start'

            # Case 3: same end, rider start somewhere on route
            elif exact_end and path:
                dist_rider_start, idx_rider_start = nearest_point_index_on_path(
                    rider_start.latitude, rider_start.longitude, path
                )
                if dist_rider_start <= ROUTE_STATION_RADIUS_KM:
                    _, idx_driver_start = nearest_point_index_on_path(
                        driver_start.latitude, driver_start.longitude, path
                    )
                    if idx_rider_start >= idx_driver_start:
                        score      = SCORE_SAME_END_ONLY
                        match_zone = 'same_end'

            # Case 4 & 5: neither exact, check route
            elif path:
                dist_rider_start, idx_rider_start = nearest_point_index_on_path(
                    rider_start.latitude, rider_start.longitude, path
                )
                dist_rider_end, idx_rider_end = nearest_point_index_on_path(
                    rider_end.latitude, rider_end.longitude, path
                )

                start_on_route = dist_rider_start <= ROUTE_STATION_RADIUS_KM
                end_on_route   = dist_rider_end   <= ROUTE_STATION_RADIUS_KM

                if start_on_route and end_on_route:
                    if idx_rider_start < idx_rider_end:
                        score      = SCORE_BOTH_ON_ROUTE
                        match_zone = 'both_on_route'
                elif start_on_route or end_on_route:
                    score      = SCORE_ONE_ON_ROUTE
                    match_zone = 'partial_route'

            if score is None:
                continue

            if time_window:
                score += SCORE_TIME_BONUS

            dist_to_driver_start = haversine(
                rider_start.latitude, rider_start.longitude,
                driver_start.latitude, driver_start.longitude
            )
            dist_to_driver_end = haversine(
                rider_end.latitude, rider_end.longitude,
                driver_end.latitude, driver_end.longitude
            )

            ride_data = RidesSerializer(ride).data
            ride_data['match_zone']              = match_zone
            ride_data['score']                   = score
            ride_data['dist_to_driver_start_km'] = round(dist_to_driver_start, 2)
            ride_data['dist_to_driver_end_km']   = round(dist_to_driver_end, 2)
            results.append(ride_data)

        results.sort(key=lambda x: x['score'], reverse=True)

        return Response({"count": len(results), "results": results}, status=status.HTTP_200_OK)
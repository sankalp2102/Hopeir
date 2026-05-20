from django.urls import path
from .views import (RideCreateView, RideListView, RideRequestCreateView,
                    RideRequestListForDriverView,
                    RideFeedbackCreateView, RideFeedbackListView,
                    RideMatchView)

urlpatterns = [
    path('create/', RideCreateView.as_view(), name='ride-create'),
    path('get/', RideListView.as_view(), name='ride-list'),
    path('match/', RideMatchView.as_view(), name='ride-match'),
    path('request/', RideRequestCreateView.as_view(), name='ride-request'),
    path('request/get/', RideRequestListForDriverView.as_view(), name='ride-request-list-driver'),
    path('feedback/post/', RideFeedbackCreateView.as_view(), name='ride-feedback'),
    path('feedback/get/', RideFeedbackListView.as_view(), name='ride-feedback-list'),
]
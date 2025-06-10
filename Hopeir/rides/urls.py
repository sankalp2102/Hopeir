from django.urls import path
from .views import (RideCreateView, RideActionView,
                    RideListView, RideRequestCreateView,
                    RideRequestRespondView, RideFeedbackCreateView, 
                    RideFeedbackListView, RideRequestListForDriverView)
urlpatterns = [
    path('create/', RideCreateView.as_view(), name='ride-create'),
    path('get/', RideListView.as_view(), name='ride-list'),
    path('request/', RideRequestCreateView.as_view(), name='ride-request'),
    path('request/get/', RideRequestListForDriverView.as_view(), name='ride-request-list-driver'),
    path('request/<int:pk>/respond/', RideRequestRespondView.as_view(), name='ride-request-respond'),
    path('rides/<int:ride_id>/<str:action>/', RideActionView.as_view(), name='ride-action'), #start, end, cancel
    path('feedback/post/', RideFeedbackCreateView.as_view(), name='ride-feedback'),
    path('feedback/get/', RideFeedbackListView.as_view(), name='ride-feedback-list'),# ride_id, from_user_id, to_user_id (?ride_id=3, )
]

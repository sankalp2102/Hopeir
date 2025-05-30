from django.urls import path
from .views import RideCreateView, RideActionView
urlpatterns = [
    path('rides/create/', RideCreateView.as_view(), name='ride-create'),
    path('rides/<int:ride_id>/<str:action>/', RideActionView.as_view(), name='ride-action'),
]

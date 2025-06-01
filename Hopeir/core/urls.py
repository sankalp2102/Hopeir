from django.urls import path
from .views import ProfileView, ProfileCreateView, VehicleProfileListCreateAPIView 
urlpatterns = [
    path('profile/create/', ProfileCreateView.as_view(), name='profile-create'),
    path('profile/<str:email>/', ProfileView.as_view(), name='profile-get-update'),
    path('vehicles/', VehicleProfileListCreateAPIView.as_view(), name='vehicles-by-user'),
]

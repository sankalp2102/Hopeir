from django.urls import path
from .views import ProfileViewByEmail, ProfileViewByUserId, ProfileCreateView, VehicleProfileListCreateAPIView 
urlpatterns = [
    path('profile/create/', ProfileCreateView.as_view(), name='profile-create'),
    path('profile/<int:user_id>/', ProfileViewByUserId.as_view(), name='profile-get-user-id'),
    path('profile/<str:email>/', ProfileViewByEmail.as_view(), name='profile-get-update-email'),
    path('vehicles/', VehicleProfileListCreateAPIView.as_view(), name='vehicles-by-user'),
]

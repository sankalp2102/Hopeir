from django.urls import path
from .views import (ProfileViewByEmail, ProfileViewByUserId, 
                    ProfileCreateView, VehicleProfileListCreateAPIView, 
                    TestAPIView, DeleteUserByEmailView)
urlpatterns = [
    path('profiles/<str:user_id>/', ProfileViewByUserId.as_view(), name='profile-get-user-id'),
    path('profile/<str:email>/', ProfileViewByEmail.as_view(), name='profile-get-update-email'),
    path('vehicles/', VehicleProfileListCreateAPIView.as_view(), name='vehicles-by-user'),
    path('profile/create/', ProfileCreateView.as_view(), name='profile-create'),
    path('Test/', TestAPIView.as_view(), name='Testing'),
    path("delete-user/", DeleteUserByEmailView.as_view(), name="delete_user"),
]

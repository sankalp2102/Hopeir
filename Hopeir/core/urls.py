from django.urls import path
from .views import (ProfileViewByEmail, ProfileViewByUserId, 
                    ProfileCreateView, VehicleProfileListCreateAPIView, 
                    TestAPIView, DeleteSuperTokensUserView)
urlpatterns = [
    path('profile/create/', ProfileCreateView.as_view(), name='profile-create'),
    path('profile/<int:user_id>/', ProfileViewByUserId.as_view(), name='profile-get-user-id'),
    path('profile/<str:email>/', ProfileViewByEmail.as_view(), name='profile-get-update-email'),
    path('vehicles/', VehicleProfileListCreateAPIView.as_view(), name='vehicles-by-user'),
    path('Test/', TestAPIView.as_view(), name='Testing'),
    path("delete-supertokens-user/", DeleteSuperTokensUserView.as_view(), name="delete_supertokens_user"),
]

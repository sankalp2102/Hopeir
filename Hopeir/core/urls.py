from django.urls import path
from .views import ProfileView, VehicleProfileListCreateAPIView

urlpatterns = [
    path('profile/', ProfileView.as_view(), name='profile'),
    path('vehicles/', VehicleProfileListCreateAPIView.as_view(), name='vehicles-by-user'),
    # path('sync-supertokens-user/', SyncSupertokensUserView.as_view(), name='sync-supertokens-user'),
]

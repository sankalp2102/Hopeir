# urls.py
from django.urls import path
from .views import RideInputCreateView, RideInputListView

urlpatterns = [
    path('post/', RideInputCreateView.as_view(), name='add-user-route'),
    path('get/', RideInputListView.as_view(), name='list-user-routes'),
]

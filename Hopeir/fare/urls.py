from django.urls import path
from .views import FareView
urlpatterns = [
    path('fares/', FareView.as_view(), name='fare-list-create'),
]

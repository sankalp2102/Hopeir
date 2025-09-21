from django.urls import path
from .views import PosterListCreateView

urlpatterns = [
    path('active/get/', PosterListCreateView.as_view(), name='active-poster'),
]

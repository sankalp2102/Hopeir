from django.urls import path
from .views import StationCreateView, StationListView
urlpatterns = [
    path('post', StationCreateView.as_view(), name='stations-list-create'),
    path('get/', StationListView.as_view(), name='stations-get'),
]

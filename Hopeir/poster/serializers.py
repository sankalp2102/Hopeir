from rest_framework import serializers
from .models import Poster

class PosterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Poster
        fields = ['id', 'title', 'image_url', 'target_url', 'is_active', 'created_at']
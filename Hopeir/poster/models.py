from django.db import models

# Create your models here.

class Poster(models.Model):
    title = models.CharField(max_length=200)
    image_url = models.URLField(max_length=1024)
    target_url = models.URLField(max_length=1024, blank=True, null=True)
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - Active: {self.is_active} - ID is {self.id}"
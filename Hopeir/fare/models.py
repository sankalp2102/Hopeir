from django.db import models

# Create your models here.
class Fare(models.Model):
    price = models.DecimalField(max_digits=10, decimal_places=2, null = True, blank=True)
    
    def __str__(self):
        return f"Fare_id {self.id} - Price: {self.price}"
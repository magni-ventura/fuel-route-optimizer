from django.db import models

# Create your models here.

class FuelStation(models.Model):
    truckstop_id = models.CharField(max_length=50)
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=10)
    rack_id = models.CharField(max_length=50, blank=True)

    # Store fuel prices as currency values, not floating-point numbers.
    retail_price = models.DecimalField(
        max_digits=10,
        decimal_places=4,
    )

    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    # Indicates whether the coordinates have been verified.
    coordinates_verified = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=["state", "city"]),
            models.Index(fields=["retail_price"]),
        ]

    def __str__(self):
        return f"{self.name} - {self.city}, {self.state}"
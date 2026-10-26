
from django.db import models
from django.contrib.gis.db import models as gis_models


class FuelStation(gis_models.Model):
    truckstop_id = models.CharField(max_length=50)
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=10)
    rack_id = models.CharField(max_length=50, blank=True)

    # PostGIS spatial point for efficient geographic queries.
    # Coordinates are stored as longitude, latitude.
    location = gis_models.PointField(
        geography=True,
        srid=4326,
        null=True,
        blank=True,
        spatial_index=True,
    )

    # Store fuel prices as currency values.
    retail_price = models.DecimalField(
        max_digits=10,
        decimal_places=4,
    )

    # Retain existing coordinate fields for compatibility.
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    coordinates_verified = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=["state", "city"]),
            models.Index(fields=["retail_price"]),
        ]

    def __str__(self):
        return f"{self.name} - {self.city}, {self.state}"

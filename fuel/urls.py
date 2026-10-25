from django.urls import path

from .views import FuelRouteAPIView

urlpatterns = [
    path(
        "v1/fuel-routes/",
        FuelRouteAPIView.as_view(),
        name="fuel-route",
    ),
]
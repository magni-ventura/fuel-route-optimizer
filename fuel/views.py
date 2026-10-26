import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import FuelStation
from .serializers import FuelRouteRequestSerializer
from .services.geocoding import geocode_location
from .services.optimizer import optimize_fuel_stops
from .services.routing import get_route
from .services.station_matching import (
    find_origin_fuel_price,
    match_stations_to_route,
)

logger = logging.getLogger(__name__)


class FuelRouteAPIView(APIView):

    def post(self, request):
        serializer = FuelRouteRequestSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        try:
            start = geocode_location(
                data["start_location"]
            )
            finish = geocode_location(
                data["finish_location"]
            )

            # Implement this helper to check the resolved
            # coordinates against the US geographic boundary.
            # It should reject locations outside the USA.

            route = get_route(start, finish)

            stations = list(
                FuelStation.objects.filter(
                    coordinates_verified=True,
                    latitude__isnull=False,
                    longitude__isnull=False,
                    retail_price__gt=0,
                ).only(
                    "truckstop_id",
                    "name",
                    "latitude",
                    "longitude",
                    "retail_price",
                )
            )

            if not stations:
                return Response(
                    {
                        "error": (
                            "No fuel stations with verified coordinates "
                            "and valid prices are available."
                        )
                    },
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )

            origin_price = find_origin_fuel_price(stations, start)
            if origin_price is None:
                return Response(
                    {
                        "error": (
                            "No fuel station with a valid price was found "
                            "within 10 miles of the origin."
                        )
                    },
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )

            matched_stations = match_stations_to_route(
                stations,
                route["geometry"],
                route["distance_miles"],
            )

            try:
                optimization = optimize_fuel_stops(
                    distance_miles=route["distance_miles"],
                    stations=matched_stations,
                    origin_price=origin_price,
                )
            except ValueError as exc:
                return Response(
                    {"error": str(exc)},
                    status=status.HTTP_422_UNPROCESSABLE_ENTITY,
                )
            
            route_summary = {
                "distance_miles": route["distance_miles"],
                "duration_seconds": route["duration_seconds"],
            }
            
            return Response(
                {
                    "start": start,
                    "finish": finish,
                    "route": route,
                    "route_summary": route_summary,
                    "optimization": optimization,
                },
                status=status.HTTP_200_OK,
            )

        except ValueError as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        except Exception:
            logger.exception("Unable to calculate the fuel route.")
            return Response(
                {"error": "Unable to calculate the route."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

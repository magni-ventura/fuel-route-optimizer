from django.shortcuts import render
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import FuelRouteRequestSerializer
from .services.geocoding import geocode_location
from .services.routing import get_route


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

            # TODO:
            # 1. Match geocoded fuel stations to route geometry.
            # 2. Find a suitable origin fuel price.
            # 3. Call optimize_fuel_stops().
            # 4. Assemble the final response.

            return Response(
                {
                    "start": start,
                    "finish": finish,
                    "route": route,
                    "message": (
                        "Routing works. Fuel station "
                        "matching and optimization must "
                        "be connected before submission."
                    ),
                },
                status=status.HTTP_200_OK,
            )

        except ValueError as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        except Exception:
            # Log the full exception on the server.
            # Do not return internal error details to clients.
            return Response(
                {"error": "Unable to calculate the route."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

from decimal import Decimal
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from django.test import RequestFactory, SimpleTestCase

from .management.commands.import_fuel_prices import Command
from .services.station_matching import (
    find_origin_fuel_price,
    match_stations_to_route,
)
from .views import FuelRouteAPIView


class ImportFuelPricesCommandTests(SimpleTestCase):
    def test_imports_quoted_comma_fields_with_padded_csv(self):
        csv_data = (
            "OPIS Truckstop ID, Truckstop Name, Address, City, State, "
            "Rack ID, Retail Price\n"
            '7, WOODSHED OF BIG CABIN, "I-44, EXIT 283 & US-69", '
            "Big Cabin, OK, 307, 3.00733333\n"
        )

        with TemporaryDirectory() as directory:
            csv_path = Path(directory) / "prices.csv"
            csv_path.write_text(csv_data, encoding="utf-8")
            output = StringIO()
            command = Command()
            command.stdout = output
            command.stderr = StringIO()

            with patch(
                "fuel.management.commands.import_fuel_prices.FuelStation"
                ".objects.update_or_create",
                return_value=(None, True),
            ) as update_or_create:
                Command.handle.__wrapped__(
                    command,
                    csv_path=str(csv_path),
                )

        update_or_create.assert_called_once_with(
            truckstop_id="7",
            name="WOODSHED OF BIG CABIN",
            city="Big Cabin",
            state="OK",
            defaults={
                "address": "I-44, EXIT 283 & US-69",
                "rack_id": "307",
                "retail_price": Decimal("3.00733333"),
            },
        )
        self.assertIn("Skipped: 0", output.getvalue())


class StationMatchingTests(SimpleTestCase):
    def setUp(self):
        self.route_geometry = {
            "type": "LineString",
            "coordinates": [
                [-100.0, 40.0],
                [-99.0, 40.0],
            ],
        }
        self.station = SimpleNamespace(
            truckstop_id="station-1",
            name="Route Fuel",
            longitude=-99.5,
            latitude=40.01,
            retail_price=2.75,
        )

    def test_matches_nearby_stations_at_route_distance(self):
        matched = match_stations_to_route(
            [self.station],
            self.route_geometry,
            route_distance_miles=70,
        )

        self.assertEqual(len(matched), 1)
        self.assertEqual(matched[0]["id"], "station-1")
        self.assertAlmostEqual(matched[0]["distance_miles"], 35, delta=1)

    def test_excludes_stations_outside_route_corridor(self):
        self.station.latitude = 40.2

        matched = match_stations_to_route(
            [self.station],
            self.route_geometry,
            route_distance_miles=70,
        )

        self.assertEqual(matched, [])

    def test_finds_nearest_station_price_at_origin(self):
        price = find_origin_fuel_price(
            [self.station],
            {"longitude": -99.5, "latitude": 40.01},
        )

        self.assertEqual(price, 2.75)


class FuelRouteAPIViewTests(SimpleTestCase):
    @patch("fuel.views.get_route")
    @patch("fuel.views.geocode_location")
    @patch("fuel.views.FuelStation.objects.filter")
    def test_post_reports_unavailable_station_data(
        self,
        filter_stations,
        geocode,
        get_route,
    ):
        geocode.side_effect = [
            {"latitude": 40.0, "longitude": -100.0},
            {"latitude": 40.0, "longitude": -99.0},
        ]
        get_route.return_value = {
            "distance_miles": 70,
            "duration_seconds": 3600,
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [-100.0, 40.0],
                    [-99.0, 40.0],
                ],
            },
        }
        filter_stations.return_value.only.return_value = []

        request = RequestFactory().post(
            "/api/v1/fuel-routes/",
            {
                "start_location": "Origin",
                "finish_location": "Destination",
            },
            content_type="application/json",
        )
        response = FuelRouteAPIView.as_view()(request)

        self.assertEqual(response.status_code, 503)
        self.assertIn("verified coordinates", response.data["error"])

    @patch("fuel.views.get_route")
    @patch("fuel.views.geocode_location")
    @patch("fuel.views.FuelStation.objects.filter")
    def test_post_includes_fuel_optimization(
        self,
        filter_stations,
        geocode,
        get_route,
    ):
        start = {
            "latitude": 40.0,
            "longitude": -100.0,
            "display_name": "Origin",
        }
        finish = {
            "latitude": 40.0,
            "longitude": -99.0,
            "display_name": "Destination",
        }
        route = {
            "distance_miles": 70,
            "duration_seconds": 3600,
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [-100.0, 40.0],
                    [-99.0, 40.0],
                ],
            },
        }
        origin_station = SimpleNamespace(
            truckstop_id="origin",
            name="Origin Fuel",
            longitude=-100.0,
            latitude=40.0,
            retail_price=2.75,
        )
        route_station = SimpleNamespace(
            truckstop_id="route",
            name="Route Fuel",
            longitude=-99.5,
            latitude=40.01,
            retail_price=2.50,
        )

        geocode.side_effect = [start, finish]
        get_route.return_value = route
        filter_stations.return_value.only.return_value = [
            origin_station,
            route_station,
        ]

        request = RequestFactory().post(
            "/api/v1/fuel-routes/",
            {
                "start_location": "Origin",
                "finish_location": "Destination",
            },
            content_type="application/json",
        )
        response = FuelRouteAPIView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertIn("optimization", response.data)
        self.assertEqual(
            response.data["optimization"]["fuel_stops"][0]["id"],
            "route",
        )
        self.assertNotIn("message", response.data)

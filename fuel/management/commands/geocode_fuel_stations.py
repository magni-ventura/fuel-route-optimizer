
import json
import logging
import time
from pathlib import Path

import requests
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Q

from fuel.models import FuelStation

logger = logging.getLogger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "FuelRouteOptimizer/1.0 (fuel station coordinate enrichment)"


class Command(BaseCommand):
    help = (
        "Geocode fuel stations missing verified coordinates "
        "and save the results to the database."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Maximum number of stations to process. Omit for all.",
        )
        parser.add_argument(
            "--delay",
            type=float,
            default=1.1,
            help="Seconds between uncached Nominatim requests (default: 1.1).",
        )

    def handle(self, *args, **options):
        limit = options["limit"]
        delay = options["delay"]

        if limit is not None and limit < 1:
            self.stderr.write(self.style.ERROR("--limit must be at least 1."))
            return

        if delay < 1.0:
            self.stderr.write(
                self.style.ERROR(
                    "Use a delay of at least 1 second for public Nominatim."
                )
            )
            return

        cache_path = Path(settings.BASE_DIR) / ".geocode_cache.json"

        try:
            cache = json.loads(cache_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            cache = {}
        except (json.JSONDecodeError, OSError) as exc:
            self.stderr.write(
                self.style.ERROR(f"Could not read geocoding cache: {exc}")
            )
            return

        stations_query = (
            FuelStation.objects.filter(
                Q(latitude__isnull=True)
                | Q(longitude__isnull=True)
                | Q(coordinates_verified=False)
            )
            .order_by("pk")
        )

        if limit is not None:
            stations_query = stations_query[:limit]

        stations = list(stations_query)
        total = len(stations)

        self.stdout.write(f"Stations requiring enrichment: {total}")

        if not stations:
            self.stdout.write(
                self.style.SUCCESS("All stations already have verified coordinates.")
            )
            return

        session = requests.Session()
        session.headers.update({"User-Agent": USER_AGENT})

        updated = 0
        failed = 0
        cache_hits = 0

        for index, station in enumerate(stations, start=1):
            address = getattr(station, "address", "") or ""
            city = getattr(station, "city", "") or ""
            state = getattr(station, "state", "") or ""

            search_address = ", ".join(
                part.strip()
                for part in (address, city, state, "USA")
                if part and part.strip()
            )

            if not address.strip() and not city.strip():
                failed += 1
                self.stdout.write(
                    f"[{index}/{total}] SKIPPED pk={station.pk}: "
                    "no usable address or city"
                )
                continue

            cache_key = search_address.casefold()

            try:
                result = cache.get(cache_key)

                if result:
                    cache_hits += 1
                else:
                    # Retry transient HTTP errors and rate limits.
                    for attempt in range(3):
                        response = session.get(
                            NOMINATIM_URL,
                            params={
                                "q": search_address,
                                "format": "jsonv2",
                                "limit": 1,
                                "countrycodes": "us",
                                "addressdetails": 1,
                            },
                            timeout=20,
                        )

                        if response.status_code == 429 or response.status_code >= 500:
                            if attempt == 2:
                                response.raise_for_status()

                            time.sleep(5 * (attempt + 1))
                            continue

                        response.raise_for_status()
                        results = response.json()
                        break
                    else:
                        results = []

                    # Enforce the public service's request rate limit.
                    time.sleep(delay)

                    if not results:
                        failed += 1
                        self.stdout.write(
                            f"[{index}/{total}] NOT FOUND: {search_address}"
                        )
                        continue

                    candidate = results[0]
                    country_code = (
                        candidate.get("address", {})
                        .get("country_code", "")
                        .lower()
                    )

                    if country_code != "us":
                        failed += 1
                        self.stdout.write(
                            f"[{index}/{total}] REJECTED non-US result: "
                            f"{search_address}"
                        )
                        continue

                    latitude = float(candidate["lat"])
                    longitude = float(candidate["lon"])

                    if not (
                        -90 <= latitude <= 90
                        and -180 <= longitude <= 180
                    ):
                        failed += 1
                        self.stdout.write(
                            f"[{index}/{total}] REJECTED invalid coordinates: "
                            f"{search_address}"
                        )
                        continue

                    result = {
                        "latitude": latitude,
                        "longitude": longitude,
                        "display_name": candidate.get("display_name", ""),
                    }

                    cache[cache_key] = result

                # Save the coordinates and verification flag to PostgreSQL.
                station.latitude = result["latitude"]
                station.longitude = result["longitude"]
                station.coordinates_verified = True

                station.save(
                    update_fields=[
                        "latitude",
                        "longitude",
                        "coordinates_verified",
                    ]
                )

                updated += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"[{index}/{total}] UPDATED pk={station.pk}: "
                        f"{station.latitude}, {station.longitude}"
                    )
                )

            except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
                failed += 1
                logger.exception(
                    "Failed to geocode fuel station pk=%s", station.pk
                )
                self.stderr.write(
                    f"[{index}/{total}] ERROR pk={station.pk}: {exc}"
                )

            finally:
                # Save the cache periodically so progress survives interruption.
                if index % 25 == 0 or index == total:
                    try:
                        cache_path.write_text(
                            json.dumps(cache, indent=2),
                            encoding="utf-8",
                        )
                    except OSError as exc:
                        self.stderr.write(
                            self.style.ERROR(
                                f"Could not save geocoding cache: {exc}"
                            )
                        )

        session.close()

        self.stdout.write("")
        self.stdout.write("Coordinate enrichment completed.")
        self.stdout.write(f"Processed: {total}")
        self.stdout.write(f"Updated: {updated}")
        self.stdout.write(f"Cache hits: {cache_hits}")
        self.stdout.write(f"Failed or not found: {failed}")
        self.stdout.write(f"Cache file: {cache_path}")

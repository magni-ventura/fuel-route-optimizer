
import logging

import requests

OSRM_URL = (
    "https://router.project-osrm.org/"
    "route/v1/driving"
)

logger = logging.getLogger(__name__)


def get_route(start, finish):
    """
    Retrieve a driving route from OSRM and remove consecutive
    duplicate coordinates from the returned route geometry.

    Args:
        start (dict): Starting location containing latitude
            and longitude.
        finish (dict): Destination containing latitude
            and longitude.

    Returns:
        dict: Route distance in miles, duration in seconds,
            and cleaned GeoJSON geometry.

    Raises:
        requests.RequestException: If the OSRM request fails.
        ValueError: If OSRM cannot provide a valid route.
        KeyError: If the OSRM response lacks required fields.
    """

    # Build the OSRM coordinate string in longitude,latitude order.
    coordinates = (
        f"{start['longitude']},{start['latitude']};"
        f"{finish['longitude']},{finish['latitude']}"
    )

    # Request the driving route from OSRM.
    response = requests.get(
        f"{OSRM_URL}/{coordinates}",
        params={
            "overview": "full",
            "geometries": "geojson",
            "steps": "false",
        },
        timeout=20,
    )

    response.raise_for_status()
    payload = response.json()

    # Validate the OSRM response.
    if payload.get("code") != "Ok" or not payload.get("routes"):
        raise ValueError(
            "A driving route could not be found."
        )

    route = payload["routes"][0]

    # OSRM returns distance in metres and duration in seconds.
    distance_miles = route["distance"] / 1609.344

    # Extract the route geometry coordinates.
    route_geometry = route["geometry"]
    coordinates = route_geometry["coordinates"]

    # Remove consecutive duplicate coordinate pairs.
    cleaned_coordinates = []

    for coordinate in coordinates:
        if (
            not cleaned_coordinates
            or coordinate != cleaned_coordinates[-1]
        ):
            cleaned_coordinates.append(coordinate)

    # Update the geometry with the cleaned coordinate list.
    route_geometry["coordinates"] = cleaned_coordinates

    # Log the cleanup results for troubleshooting.
    removed_count = len(coordinates) - len(cleaned_coordinates)

    logger.info(
        "Route coordinate cleanup completed: "
        "%s original, %s retained, %s consecutive duplicates removed.",
        len(coordinates),
        len(cleaned_coordinates),
        removed_count,
    )

    # Return the route in the format expected by the existing API.
    return {
        "distance_miles": distance_miles,
        "duration_seconds": route["duration"],
        "geometry": route_geometry,
    }

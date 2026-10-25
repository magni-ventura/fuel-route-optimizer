import requests

OSRM_URL = (
    "https://router.project-osrm.org/"
    "route/v1/driving"
)


def get_route(start, finish):
    coordinates = (
        f"{start['longitude']},{start['latitude']};"
        f"{finish['longitude']},{finish['latitude']}"
    )

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

    if payload.get("code") != "Ok" or not payload.get("routes"):
        raise ValueError(
            "A driving route could not be found."
        )

    route = payload["routes"][0]

    # OSRM returns distance in metres and duration in seconds.
    distance_miles = route["distance"] / 1609.344

    return {
        "distance_miles": distance_miles,
        "duration_seconds": route["duration"],
        "geometry": route["geometry"],
    }
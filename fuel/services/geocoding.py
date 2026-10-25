import requests

GEOCODING_URL = (
    "https://nominatim.openstreetmap.org/search"
)


def geocode_location(location):
    response = requests.get(
        GEOCODING_URL,
        params={
            "q": location,
            "format": "jsonv2",
            "limit": 1,
            "countrycodes": "us",
        },
        headers={
            "User-Agent": (
                "FuelRouteOptimizer/1.0 "
                "(assessment prototype)"
            ),
        },
        timeout=10,
    )

    response.raise_for_status()
    results = response.json()

    if not results:
        raise ValueError(
            f"Location not found in the USA: {location}"
        )

    result = results[0]

    return {
        "latitude": float(result["lat"]),
        "longitude": float(result["lon"]),
        "display_name": result["display_name"],
    }
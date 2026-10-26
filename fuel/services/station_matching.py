import math

EARTH_RADIUS_MILES = 3958.7613
MAX_ROUTE_DISTANCE_MILES = 10
MAX_ORIGIN_STATION_DISTANCE_MILES = 10


def _distance_miles(first, second):
    longitude_1, latitude_1 = map(math.radians, first)
    longitude_2, latitude_2 = map(math.radians, second)

    latitude_delta = latitude_2 - latitude_1
    longitude_delta = longitude_2 - longitude_1

    haversine = (
        math.sin(latitude_delta / 2) ** 2
        + math.cos(latitude_1)
        * math.cos(latitude_2)
        * math.sin(longitude_delta / 2) ** 2
    )

    return 2 * EARTH_RADIUS_MILES * math.asin(
        math.sqrt(haversine)
    )


def _project_station_onto_segment(station, start, finish):
    mean_latitude = math.radians(
        (station[1] + start[1] + finish[1]) / 3
    )
    longitude_scale = math.cos(mean_latitude)

    def project(point):
        return (
            math.radians(point[0]) * longitude_scale,
            math.radians(point[1]),
        )

    station_x, station_y = project(station)
    start_x, start_y = project(start)
    finish_x, finish_y = project(finish)

    segment_x = finish_x - start_x
    segment_y = finish_y - start_y
    segment_length_squared = segment_x**2 + segment_y**2

    if segment_length_squared == 0:
        fraction = 0.0
    else:
        fraction = (
            (station_x - start_x) * segment_x
            + (station_y - start_y) * segment_y
        ) / segment_length_squared
        fraction = min(1.0, max(0.0, fraction))

    closest = (
        start_x + fraction * segment_x,
        start_y + fraction * segment_y,
    )
    offset_miles = math.hypot(
        station_x - closest[0],
        station_y - closest[1],
    ) * EARTH_RADIUS_MILES

    return fraction, offset_miles


def match_stations_to_route(
    stations,
    route_geometry,
    route_distance_miles,
    max_distance_miles=MAX_ROUTE_DISTANCE_MILES,
):
    coordinates = route_geometry.get("coordinates", [])
    if len(coordinates) < 2:
        raise ValueError("Route geometry must contain at least two points.")

    geometry_segments = []
    geometry_distance = 0.0

    for start, finish in zip(coordinates, coordinates[1:]):
        segment_distance = _distance_miles(start, finish)
        geometry_segments.append(
            (start, finish, geometry_distance, segment_distance)
        )
        geometry_distance += segment_distance

    if (
        not math.isfinite(route_distance_miles)
        or route_distance_miles <= 0
        or geometry_distance <= 0
    ):
        raise ValueError("Route distance must be positive.")

    matched = []

    for station in stations:
        station_point = (station.longitude, station.latitude)
        if (
            not all(math.isfinite(value) for value in station_point)
            or not -180 <= station.longitude <= 180
            or not -90 <= station.latitude <= 90
        ):
            continue

        nearest_offset = math.inf
        nearest_position = 0.0

        for start, finish, segment_start, segment_distance in geometry_segments:
            fraction, offset = _project_station_onto_segment(
                station_point, start, finish
            )

            if offset < nearest_offset:
                nearest_offset = offset
                nearest_position = segment_start + fraction * segment_distance

        if nearest_offset > max_distance_miles:
            continue

        matched.append(
            {
                "id": station.truckstop_id,
                "name": station.name,
                "distance_miles": (
                    nearest_position / geometry_distance
                    * route_distance_miles
                ),
                "price_per_gallon": float(station.retail_price),
            }
        )

    return matched


def find_origin_fuel_price(
    stations,
    start,
    max_distance_miles=MAX_ORIGIN_STATION_DISTANCE_MILES,
):
    start_point = (start["longitude"], start["latitude"])
    nearby_stations = []

    for station in stations:
        station_point = (station.longitude, station.latitude)
        if (
            not all(math.isfinite(value) for value in station_point)
            or not -180 <= station.longitude <= 180
            or not -90 <= station.latitude <= 90
        ):
            continue

        distance = _distance_miles(start_point, station_point)
        if distance <= max_distance_miles and station.retail_price > 0:
            nearby_stations.append((distance, station))

    if not nearby_stations:
        return None

    _, nearest_station = min(nearby_stations, key=lambda item: item[0])
    return float(nearest_station.retail_price)

import math


def optimize_fuel_stops(
    distance_miles,
    stations,
    mpg=10,
    max_range=500,
    origin_price=None,
):
    """
    Each station must contain:
        id, name, distance_miles, price_per_gallon

    The route must be preprocessed so station distances
    represent positions along the driving route.

    Cost model:
        Fuel consumed on each leg is priced at the
        departure node's price.
    """

    if distance_miles <= 0:
        raise ValueError(
            "Route distance must be positive."
        )

    if mpg <= 0 or max_range <= 0:
        raise ValueError(
            "MPG and maximum range must be positive."
        )

    if origin_price is None or origin_price <= 0:
        raise ValueError(
            "A valid origin fuel price is required."
        )

    # Keep stations on the route, in route order.
    candidates = []

    for station in stations:
        position = float(station["distance_miles"])
        price = float(station["price_per_gallon"])

        if (
            0 < position < distance_miles
            and price > 0
            and math.isfinite(position)
            and math.isfinite(price)
        ):
            candidates.append(station)

    candidates.sort(
        key=lambda station: station["distance_miles"]
    )

    # Node zero is the origin.
    # The final node is the destination.
    nodes = [
        {
            "id": "origin",
            "name": "Origin",
            "distance_miles": 0.0,
            "price_per_gallon": origin_price,
        },
        *candidates,
        {
            "id": "destination",
            "name": "Destination",
            "distance_miles": distance_miles,
            "price_per_gallon": None,
        },
    ]

    n = len(nodes)
    infinity = float("inf")

    best_cost = [infinity] * n
    previous = [None] * n

    best_cost[0] = 0.0

    for j in range(1, n):
        for i in range(j):
            leg_distance = (
                nodes[j]["distance_miles"]
                - nodes[i]["distance_miles"]
            )

            if leg_distance < 0:
                continue

            if leg_distance > max_range:
                continue

            if not math.isfinite(best_cost[i]):
                continue

            price = nodes[i]["price_per_gallon"]

            leg_cost = (
                leg_distance / mpg
            ) * price

            proposed_cost = best_cost[i] + leg_cost

            if proposed_cost < best_cost[j]:
                best_cost[j] = proposed_cost
                previous[j] = i

    destination_index = n - 1

    if not math.isfinite(best_cost[destination_index]):
        raise ValueError(
            "No feasible fuel stop sequence was found."
        )

    path = []
    index = destination_index

    while index is not None:
        path.append(nodes[index])
        index = previous[index]

    path.reverse()

    return {
        "estimated_total_cost": round(
            best_cost[destination_index], 2
        ),
        "fuel_stops": [
            {
                "id": node["id"],
                "name": node["name"],
                "distance_miles": round(
                    node["distance_miles"], 2
                ),
                "price_per_gallon": node[
                    "price_per_gallon"
                ],
            }
            for node in path[1:-1]
        ],
        "path": path,
    }
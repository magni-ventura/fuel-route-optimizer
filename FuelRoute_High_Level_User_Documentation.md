# FuelRoute Optimizer --- High-Level User Guide

**Audience:** Users, testers, reviewers and non-technical stakeholders\
**Purpose:** Explain the intended workflow without requiring knowledge
of the codebase.

## 1. What is FuelRoute Optimizer?

FuelRoute Optimizer is a journey-planning backend designed to help a
driver travel between two locations in the United States while
considering fuel costs along the way. It combines road-route information
with a supplied fuel-price dataset to support fuel-stop recommendations.
The API can be tested with Postman or consumed by a user interface.

The assessment assumptions are a maximum vehicle range of **500 miles**
and fuel economy of **10 miles per gallon (MPG)**. These are calculation
assumptions, not a guarantee of real-world vehicle performance.

The exact fields returned to users depend on the current API
implementation.

## 2. What information does it use?

### Journey locations

The user provides a start location and a destination within the United
States. The system needs geographic coordinates to calculate a road
route.

### Road route

A routing service supplies road-route information. Distance and route
geometry can be used to estimate fuel needs and display a journey on a
map.

### Fuel-price data

The CSV discussed during development contains: - OPIS Truckstop ID -
Truckstop Name - Address - City - State - Rack ID - Retail Price

The source CSV does **not** contain latitude/longitude. The system
therefore needs station coordinate enrichment before it can reliably
determine which stations are near a route. Fuel prices are only as
current as the supplied dataset or latest import; they should not be
treated as live pump prices unless the application explicitly fetches
live data.

## 3. Typical journey workflow

1.  **Enter the journey:** Provide the start and destination in the
    format required by the API or user interface.
2.  **Submit the request:** The client sends the request to the backend.
3.  **Calculate the route:** The backend obtains driving-route
    information from its routing provider.
4.  **Evaluate fuel options:** Eligible stations and their prices are
    compared along or near the route.
5.  **Review the result:** Depending on the implemented response, the
    result may include route details, map geometry, fuel-stop
    recommendations and cost estimates.
6.  **Correct and retry:** If input validation fails, correct the
    location or required fields and submit again.

Use the actual endpoint and input field names from the current
application. This guide intentionally does not invent an unverified API
request format.

## 4. Testing with Postman

Postman sends requests directly to the backend and shows the HTTP
response.

1.  Start the backend in the development environment.
2.  Create a request in Postman.
3.  Enter the actual API URL and required HTTP method from the project's
    URL configuration.
4.  If JSON is required, select **Body → raw → JSON** and enter the
    required fields.
5.  Click **Send**.
6.  Review the HTTP status and response body.
7.  If the request fails, check the server logs or provide sanitized
    diagnostic details to the maintainer.

Do not assume that a sample path such as `/api/health/` exists unless it
has been added to the project.

### Common HTTP results

  -----------------------------------------------------------------------------
  Status/result                 General meaning         Suggested action
  ----------------------------- ----------------------- -----------------------
  `200 OK`                      Request succeeded       Review the returned
                                                        route and cost details

  `201 Created`                 A resource was created, Review the created
                                if supported            resource

  `400 Bad Request`             Input is invalid or     Check required fields
                                incomplete              and JSON syntax

  `401 Unauthorized`            Authentication may be   Provide the required
                                required                credentials

  `403 Forbidden`               Request is not          Check access
                                permitted               permissions

  `404 Not Found`               URL/resource was not    Check the endpoint path
                                found                   

  `500 Internal Server Error`   Unexpected server-side  Check logs and contact
                                problem                 the maintainer

  Timeout/connection error      Server or external      Check server status and
                                service may be          logs
                                unavailable             
  -----------------------------------------------------------------------------

These are general meanings. Actual status codes depend on the
implementation.

## 5. Understanding fuel estimates

Using the assessment's 10 MPG assumption:

**Estimated gallons = journey distance in miles ÷ 10**

For example, 300 miles corresponds to an estimated 30 gallons under this
simplified assumption.

**Estimated fuel cost = estimated gallons × price per gallon**

This simple calculation alone does not decide where to stop. A valid
stop plan also needs to account for available fuel, the 500-mile range
limit, station locations, and how much fuel is purchased at each stop.

Treat estimates as dependent on the input locations, price dataset,
route provider, vehicle assumptions and implemented algorithm. They are
not guarantees of actual fuel use or station availability.

## 6. Reviewing fuel-stop recommendations

If the API returns fuel stops, review: - Station name and location. -
Listed fuel price. - Position along the route. - Whether the leg to the
next stop fits within the assumed vehicle range. - Estimated cost and
stated assumptions.

A low price does not by itself make a station a suitable stop. The
station must be reachable on or near the route, and the vehicle must be
able to reach the next stop. If no suitable station is found, the system
should communicate the limitation rather than invent a recommendation.

Exact result fields depend on the API response.

## 7. Common problems

**Location cannot be found:** Check spelling and provide a fuller city,
state or address. Confirm the location is within the supported country.

**Request is rejected:** Check the endpoint path, HTTP method, JSON
formatting and required fields.

**Route request fails:** The routing provider may be unavailable, the
location may not connect to a routable road, or the request may time
out.

**No fuel stops are returned:** The data may not cover the route,
station coordinates may be missing, or no station may meet the route and
range constraints.

**Server returns an error:** Give the maintainer the endpoint path, HTTP
method, request time, status code, sanitized response body, and request
ID header if one is returned. Never share passwords or access tokens.

## 8. Data and service limitations

Results depend on: - Correct and sufficiently current fuel prices. -
Accurate station coordinates. - Correct start and destination input. -
The 500-mile and 10-MPG assessment assumptions. - Routing/geocoding
service availability. - The actual stop-selection algorithm.

External routing and geocoding services can have outages and usage
limits. Station coordinate matching depends on the data-enrichment
process, as the source CSV lacks coordinates.

## 9. Privacy and safe use

Do not submit confidential information unless the application explicitly
requires and protects it. Do not share raw logs or Postman collections
publicly if they contain personal information, credentials or API keys.
Django admin credentials should be limited to authorized administrators.

## 10. Quick checklist before reporting an issue

-   [ ] I used the correct API URL and HTTP method.
-   [ ] I supplied the required fields in the expected format.
-   [ ] I checked the status code and response body.
-   [ ] I recorded when the failure happened.
-   [ ] I removed credentials and personal information from the report.
-   [ ] I included the request ID, if provided.

## 11. Support handover

For technical support, provide the request method, endpoint path, status
code, sanitized response body, approximate request time and request ID
if available. The maintainer can use these details to locate
corresponding logs and investigate validation, database, routing,
geocoding or other failures.

**End of high-level user documentation.**

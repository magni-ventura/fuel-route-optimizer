# FuelRoute Optimizer --- Technical Developer Documentation

**Project:** FuelRoute Optimizer\
**Stack discussed:** Python 3.13, Django 6.1.2, Django REST Framework,
PostgreSQL\
**Development environment:** Windows, VS Code, Git Bash\
**Updated:** 25 October 2026

> **Accuracy note:** This document consolidates the project
> requirements, setup steps, errors, and fixes discussed in our chats.
> The full final source for every model, view, serializer, and URL was
> not present in the conversation. Confirm exact endpoint paths, model
> fields, response schemas, and implemented algorithms in the repository
> before treating them as definitive.

## 1. Purpose and requirements

FuelRoute Optimizer is a backend API intended to accept a start and
finish location within the United States, return driving-route
information suitable for mapping, and recommend cost-effective fuel
stops.

Assessment assumptions and requirements discussed: - Maximum vehicle
range: **500 miles**. - Fuel economy: **10 miles per gallon (MPG)**. -
Fuel prices sourced from `fuel-prices-for-be-assessment.csv`. - Use
Django and PostgreSQL. - Use a free routing service and keep
routing/geocoding calls efficient, ideally around one routing call and
roughly two to three external calls per request where practical. - Test
the backend with Postman.

The source CSV contains station identifiers, names, text addresses,
city, state, rack ID and retail price. It does **not** contain
latitude/longitude, so stations must be geocoded or otherwise enriched
before accurate route-corridor matching is possible. The route API uses
only `FuelStation` records marked `coordinates_verified` with non-null
coordinates and a positive retail price. It matches stations within 10
miles of the route and requires a priced station within 10 miles of the
origin to establish the starting fuel price.

## 2. Architecture

  -----------------------------------------------------------------------
  Component                           Responsibility
  ----------------------------------- -----------------------------------
  Django                              Settings, URL routing, middleware,
                                      admin and application framework

  Django REST Framework               API request handling and JSON
                                      responses

  PostgreSQL                          Persistent application and
                                      fuel-station data

  `fuel` app                          Application-specific code;
                                      registered in `INSTALLED_APPS`

  CSV management command              Imports fuel prices into the
                                      database

  OSRM (discussed)                    Routing; can return route geometry
                                      as GeoJSON

  Nominatim (discussed)               Geocoding locations to coordinates

  Postman                             Manual API testing

  React/Vite/TypeScript frontend      Possible client UI; route logic
  (discussed)                         should remain in the backend
  -----------------------------------------------------------------------

The routing/geocoding approach was discussed, but verify the configured
provider URLs and current implementation before changing them or
claiming a provider is active.

### Intended request flow

1.  Validate the start and finish inputs.
2.  Geocode locations when coordinates are not already available or
    cached.
3.  Request a driving route.
4.  Read route distance and geometry.
5.  Identify stations near the route.
6.  Select stops that respect vehicle range and fuel-cost constraints.
7.  Return route and stop information as JSON.

The API endpoint is `POST /api/v1/fuel-routes/`, accepting
`start_location` and `finish_location`. A successful response includes
`start`, `finish`, `route` and `optimization` objects. Fuel data that
cannot support an origin price returns HTTP 503; an infeasible stop
sequence returns HTTP 422. The optimizer uses the documented 500-mile
maximum range and 10 MPG assumptions.

## 3. Project layout

The paths discussed suggest a layout similar to:

``` text
fuel-route-optimizer/
├── manage.py
├── .env
├── config/
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
├── fuel/
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   ├── admin.py
│   ├── migrations/
│   └── management/commands/import_fuel_prices.py
├── data/fuel-prices-for-be-assessment.csv
├── logs/
└── venv/
```

Verify the actual repository tree. Keep `.env`, credentials, and other
secrets out of source control.

## 4. Local setup

From Windows Git Bash:

``` bash
cd ~/Documents/Projects/fuel-route-optimizer
source venv/Scripts/activate
```

If the environment is already active, skip activation. The project was
developed using Python 3.13 and Django 6.1.2.

Install the project's dependencies using its actual dependency file, if
present:

``` bash
pip install -r requirements.txt
```

The settings load the project-root `.env` using:

``` python
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
```

Environment variable names discussed:

``` dotenv
SECRET_KEY=replace-with-a-secure-secret
DB_NAME=fuel_route_db
DB_USER=fuel_app
DB_PASSWORD=replace-with-your-database-password
DB_HOST=127.0.0.1
DB_PORT=5432
```

Use the real values from your environment; never publish passwords. For
production, set `DEBUG = False`, use a secure secret, and restrict
`ALLOWED_HOSTS`.

Run:

``` bash
python manage.py check
python manage.py migrate
python manage.py runserver
```

Use `runserver`, not `run server`. The development server typically
listens at `http://127.0.0.1:8000/`; it is not a production server.

## 5. PostgreSQL configuration and migrations

The project moved from the default SQLite configuration to PostgreSQL.
Keep only one active `DATABASES` dictionary in `config/settings.py`.

### Schema permission error

A migration previously failed with
`permission denied for schema public`. The discussed fix was to connect
as a database administrator to the correct database and grant schema
access to the application's database role, for example:

``` sql
GRANT USAGE, CREATE ON SCHEMA public TO fuel_app;
```

Replace `fuel_app` if your configured role differs. Run this only
against the intended database with an appropriately privileged account.
After correcting permissions:

``` bash
python manage.py migrate
```

The conversation later reported that migrations succeeded and there were
no migrations left to apply.

If migration errors recur, verify `.env`, PostgreSQL availability,
database name, role permissions, and `python manage.py showmigrations`.
Do not delete migrations or drop the database as a first troubleshooting
step.

## 6. Importing fuel prices

### CSV schema

The source header was confirmed as:

``` csv
OPIS Truckstop ID,Truckstop Name,Address,City,State,Rack ID,Retail Price
```

Example:

``` csv
7,WOODSHED OF BIG CABIN,"I-44, EXIT 283 & US-69",Big Cabin,OK,307,3.00733333
```

Addresses can contain commas, so use Python's `csv` module and
`csv.DictReader`; do not split each row manually on commas.

### Management command

The intended path is:

``` text
fuel/management/commands/import_fuel_prices.py
```

Ensure package `__init__.py` files exist in `fuel/management/` and
`fuel/management/commands/` as needed. The app must be registered in
`INSTALLED_APPS`.

Run from the project root:

``` bash
python manage.py import_fuel_prices data/fuel-prices-for-be-assessment.csv
```

Adjust the CSV path if the file is stored elsewhere. The discussed
implementation uses `DictReader`, `Decimal`, and
`FuelStation.objects.update_or_create(...)`, and reports created,
updated and skipped records. Confirm the exact uniqueness fields and
current model in `fuel/models.py`.

### Errors encountered

**`Unknown command: 'import_fuel_prices'`** - Check the file path and
exact filename. - Ensure management and commands directories are Python
packages where required. - Confirm `fuel` is in `INSTALLED_APPS`.

**`The CSV is missing required columns.`** - Confirm the correct CSV was
supplied. - Normalize headers with `strip()` and remove a UTF-8 BOM with
`lstrip("\\ufeff")`. - Use `encoding="utf-8-sig"`. - Print both missing
and detected headers in the command's error message.

After import, inspect the counts and sample records, confirm prices are
positive, and verify that a second import does not create unwanted
duplicates.

### Coordinates limitation

The CSV has no coordinates. Do not geocode thousands of stations during
every route request. Prefer a one-time or controlled batch enrichment
process, persist coordinates, cache results, and respect the selected
geocoder's usage policy and rate limits.

## 7. Django admin superuser

Create an administrator account:

``` bash
python manage.py createsuperuser
```

Follow the interactive prompts for username, email and password. Then
run:

``` bash
python manage.py runserver
```

Open `http://127.0.0.1:8000/admin/`.

The Django superuser grants access to Django admin. It does not
automatically create API-token authentication or prove that API
endpoints require authentication. Check DRF authentication and
permissions in the actual configuration and views.

## 8. Postman API testing

1.  Start the server with `python manage.py runserver`.
2.  Find the actual endpoint in `config/urls.py` and `fuel/urls.py`.
3.  Select the required HTTP method.
4.  If the endpoint expects JSON, select **Body → raw → JSON** and set
    `Content-Type: application/json`.
5.  Send the request and inspect the HTTP status, response body, and
    headers.
6.  Test valid inputs, missing fields, invalid locations, unavailable
    routes, external API failures, and database failures.

Do not assume that `/api/health/` exists: it was suggested as an example
diagnostic endpoint, but the conversation does not establish that it was
added to the final app.

Suggested test matrix:

  Case                          Expected behavior to verify
  ----------------------------- -----------------------------------------------
  Valid US locations            Successful response with route/result data
  Missing or invalid fields     Clear validation response
  Location cannot be geocoded   Controlled error
  No route available            Controlled error
  Routing service times out     Logged timeout and controlled API error
  No eligible stations          Explicit no-stop/coverage outcome
  Invalid JSON                  Appropriate 4xx response
  Unexpected exception          500 response and server-side traceback
  Database unavailable          Logged failure and controlled server response

The precise response fields and status codes must match the implemented
API contract.

## 9. Logging and diagnostics

The original logging setup wrote file logs at `ERROR` level, so
successful requests and normal application events were not recorded in
the file. It also lacked a dedicated `fuel` logger.

A more comprehensive configuration was discussed with: -
`application.log` for general application activity. - `errors.log` for
error and critical messages. - Console logging. - Rotating files. -
Loggers for `fuel`, `django`, `django.request`, `django.server`, and
database errors. - Optional middleware to log request IDs, method, path,
HTTP status and duration.

The proposed middleware location/class was:

``` text
fuel/middleware.py
fuel.middleware.RequestResponseLoggingMiddleware
```

It must be registered in `MIDDLEWARE` before expecting request logs or
an `X-Request-ID` response header. Confirm it is present in the actual
code.

Application logging example:

``` python
import logging

logger = logging.getLogger("fuel")

logger.info("Route calculation started")
logger.warning("No eligible stations found")
logger.error("Routing provider returned an unsuccessful status")
logger.exception("Route calculation failed unexpectedly")
```

`logger.exception()` should be called inside an exception handler to
include the traceback. Log request ID, provider status and timing where
useful, but never log passwords, authorization headers, API keys, or
unnecessary personal data.

Response-body logging was discussed as an optional development feature
controlled by `LOG_API_RESPONSE_BODIES`. Keep it disabled by default,
especially in production. Basic redaction is not a guarantee that every
sensitive value is removed.

Django cannot capture every issue outside its process, such as
PostgreSQL service crashes, operating-system termination, proxy
failures, or network outages that prevent a request reaching Django.
Those require database, operating-system, hosting or proxy logs.

## 10. Routing and optimization considerations

The OSRM URL shape discussed was:

``` text
/route/v1/driving/{coordinates}?overview=full&geometries=geojson&steps=false
```

Use the configured provider host and verify coordinate ordering. OSRM
commonly expects longitude,latitude coordinate pairs.

Nominatim was discussed for geocoding. Cache results and respect
provider policies and rate limits.

With the assessment assumptions:

``` text
estimated gallons = distance in miles / 10
estimated fuel cost = estimated gallons × price per gallon
```

These formulas are simplified estimates. A valid stop plan must account
for current usable fuel, the 500-mile maximum range, station positions,
and the amount purchased at each stop. Dynamic programming was discussed
as one possible optimization technique; verify the actual algorithm
before describing it as implemented.

Performance practices: - Cache geocoding results. - Persist station
coordinates. - Filter stations near the route corridor. - Avoid repeated
database queries inside loops. - Add database indexes based on actual
queries. - Log external request durations and failures. - Test distances
near and beyond the 500-mile range.

## 11. Troubleshooting reference

  ---------------------------------------------------------------------------
  Symptom                                 Checks
  --------------------------------------- -----------------------------------
  `BASE_DIR` referenced before assignment Define `BASE_DIR` before
                                          `load_dotenv(BASE_DIR / ".env")`

  Duplicate `DATABASES` blocks            Keep one active configuration

  `Unknown command: import_fuel_prices`   Verify command path, package files,
                                          app registration

  CSV header validation error             Verify file and normalize
                                          BOM/whitespace

  `permission denied for schema public`   Verify schema permissions for app
                                          role

  Successful requests absent from file    Set handler to `INFO`/`DEBUG` and
  log                                     emit log messages

  Postman 404                             Check endpoint path, method and URL
                                          patterns

  Postman 400                             Check JSON syntax, required fields,
                                          content type and host validation

  Postman 500                             Inspect terminal and `errors.log`
                                          traceback

  Routing/geocoding failure               Add timeouts, log provider status
                                          and return a controlled error

  Admin login failure                     Check migrations, credentials,
                                          server URL and target database
  ---------------------------------------------------------------------------

## 12. Production-readiness checklist

-   Set `DEBUG = False` and configure trusted hosts.
-   Keep credentials out of source control.
-   Verify API authentication and permissions.
-   Do not expose tracebacks to clients in production.
-   Disable response-body logging by default.
-   Restrict and rotate log files.
-   Add input validation and request-size limits.
-   Set timeouts for external providers.
-   Add tests for success and failure paths.
-   Review database permissions and backups.
-   Use a production WSGI/ASGI server.
-   Confirm provider usage policies.
-   Document real endpoint paths, request/response schemas and status
    codes from the codebase.

## 13. Command reference

``` bash
# Activate virtual environment in Windows Git Bash
source venv/Scripts/activate

# Check configuration
python manage.py check

# Create migrations after model changes
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Import fuel prices
python manage.py import_fuel_prices data/fuel-prices-for-be-assessment.csv

# Create admin account
python manage.py createsuperuser

# Run local server
python manage.py runserver

# Inspect migrations
python manage.py showmigrations

# Follow logs in Git Bash
tail -f logs/application.log
tail -f logs/errors.log
```

**End of technical developer documentation.**

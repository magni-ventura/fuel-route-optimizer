
# fuel/management/commands/import_fuel_prices.py

import csv
from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from fuel.models import FuelStation


class Command(BaseCommand):
    help = "Import fuel prices from the assessment CSV."

    REQUIRED_COLUMNS = {
        "OPIS Truckstop ID",
        "Truckstop Name",
        "Address",
        "City",
        "State",
        "Rack ID",
        "Retail Price",
    }

    def add_arguments(self, parser):
        parser.add_argument(
            "csv_path",
            type=str,
            help="Path to the fuel prices CSV file.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        csv_path = options["csv_path"]

        created = 0
        updated = 0
        skipped = 0

        try:
            file_handle = open(
                csv_path,
                "r",
                encoding="utf-8-sig",
                newline="",
            )
        except OSError as exc:
            raise CommandError(
                f"Unable to open CSV file '{csv_path}': {exc}"
            ) from exc

        with file_handle:
            reader = csv.DictReader(file_handle, skipinitialspace=True)

            # Validate and normalize the CSV headers.
            if not reader.fieldnames:
                raise CommandError(
                    "The CSV file is empty or has no header row."
                )

            reader.fieldnames = [
                header.strip().lstrip("\ufeff")
                for header in reader.fieldnames
            ]

            missing_columns = (
                self.REQUIRED_COLUMNS - set(reader.fieldnames)
            )

            if missing_columns:
                raise CommandError(
                    "The CSV is missing required columns: "
                    f"{', '.join(sorted(missing_columns))}. "
                    f"Columns found: {reader.fieldnames}"
                )

            self.stdout.write(
                f"Importing fuel prices from: {csv_path}"
            )

            for row_number, row in enumerate(reader, start=2):
                try:
                    # Skip malformed rows with extra or missing values.
                    if None in row or any(
                        value is None for value in row.values()
                    ):
                        skipped += 1
                        self.stderr.write(
                            f"Skipping row {row_number}: "
                            "incorrect number of CSV fields."
                        )
                        continue

                    truckstop_id = (
                        row["OPIS Truckstop ID"] or ""
                    ).strip()

                    name = (
                        row["Truckstop Name"] or ""
                    ).strip()

                    address = (
                        row["Address"] or ""
                    ).strip()

                    city = (
                        row["City"] or ""
                    ).strip()

                    state = (
                        row["State"] or ""
                    ).strip().upper()

                    rack_id = (
                        row["Rack ID"] or ""
                    ).strip()

                    price_text = (
                        row["Retail Price"] or ""
                    ).strip()

                    # Validate required identifying information.
                    if not all(
                        [truckstop_id, name, city, state, price_text]
                    ):
                        skipped += 1
                        self.stderr.write(
                            f"Skipping row {row_number}: "
                            "one or more required values are empty."
                        )
                        continue

                    # Parse and validate the retail price.
                    try:
                        price = Decimal(price_text)
                    except InvalidOperation as exc:
                        skipped += 1
                        self.stderr.write(
                            f"Skipping row {row_number}: "
                            f"invalid retail price '{price_text}'."
                        )
                        continue

                    if not price.is_finite() or price <= 0:
                        skipped += 1
                        self.stderr.write(
                            f"Skipping row {row_number}: "
                            "retail price must be a positive number."
                        )
                        continue

                    # Match your existing FuelStation model fields.
                    # The combination below identifies a price record.
                    _, was_created = (
                        FuelStation.objects.update_or_create(
                            truckstop_id=truckstop_id,
                            name=name,
                            city=city,
                            state=state,
                            defaults={
                                "address": address,
                                "rack_id": rack_id,
                                "retail_price": price,
                            },
                        )
                    )

                    if was_created:
                        created += 1
                    else:
                        updated += 1

                except (AttributeError, TypeError, ValueError) as exc:
                    skipped += 1
                    self.stderr.write(
                        f"Skipping row {row_number}: {exc}"
                    )

                if (created + updated + skipped) % 500 == 0:
                    self.stdout.write(
                        f"Processed {created + updated + skipped} rows..."
                    )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "Fuel price import completed.\n"
                f"Created: {created}\n"
                f"Updated: {updated}\n"
                f"Skipped: {skipped}\n"
                f"Total processed: {created + updated + skipped}"
            )
        )

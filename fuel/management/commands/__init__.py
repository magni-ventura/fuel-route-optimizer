# fuel/management/commands/import_fuel_prices.py

import csv
from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand, CommandError

from fuel.models import FuelStation


class Command(BaseCommand):
    help = "Import fuel prices from the assessment CSV."

    def add_arguments(self, parser):
        parser.add_argument("csv_path", type=str)

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
                f"Unable to open CSV: {exc}"
            ) from exc

        with file_handle:
            reader = csv.DictReader(file_handle)

            required = {
                "OPIS Truckstop ID",
                "Truckstop Name",
                "Address",
                "City",
                "State",
                "Rack ID",
                "Retail Price",
            }

            if not required.issubset(set(reader.fieldnames or [])):
                raise CommandError(
                    "The CSV is missing required columns."
                )

            for row in reader:
                try:
                    price = Decimal(
                        row["Retail Price"].strip()
                    )

                    if not price.is_finite() or price <= 0:
                        skipped += 1
                        continue

                    truckstop_id = row[
                        "OPIS Truckstop ID"
                    ].strip()

                    name = row["Truckstop Name"].strip()
                    city = row["City"].strip()
                    state = row["State"].strip().upper()

                    if not truckstop_id or not name:
                        skipped += 1
                        continue

                    station, was_created = (
                        FuelStation.objects.update_or_create(
                            truckstop_id=truckstop_id,
                            name=name,
                            city=city,
                            state=state,
                            defaults={
                                "address": row["Address"].strip(),
                                "rack_id": row["Rack ID"].strip(),
                                "retail_price": price,
                            },
                        )
                    )

                    if was_created:
                        created += 1
                    else:
                        updated += 1

                except (InvalidOperation, AttributeError, ValueError):
                    skipped += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Created: {created}; "
                f"Updated: {updated}; "
                f"Skipped: {skipped}"
            )
        )
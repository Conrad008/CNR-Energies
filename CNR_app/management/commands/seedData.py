import os
import secrets
from django.db import transaction

from django.core.management.base import BaseCommand
from CNR_app.models import User, Station, FuelProduct, Tank, Pump, Nozzle

class Command(BaseCommand):
    help = "Seeds initial fuel products, station hardware, and admin user for CNR Energies"

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write("Seeding database...")

        admin, created = User.objects.get_or_create(
            email="admin@cnrenergies.com",
            defaults={
                "first_name": "Conrad",
                "role": User.Role.SUPER_ADMIN,
                "is_staff": True,
                "is_superuser": True,
            },
        )
        if created:
            password = os.environ.get("PASSWORD")
            if not password:
                password = secrets.token_urlsafe(16)
                self.stdout.write(
                    self.style.WARNING(
                        f"PASSWORD not set — generated random password: {password}\n"
                        "Store this securely; it will not be shown again."
                    )
                )
            admin.set_password(password)
            admin.save()
            self.stdout.write(self.style.SUCCESS("Superuser admin@cnrenergies.com created."))
        else:
            self.stdout.write("Superuser already exists — skipping password assignment.")

        station, _ = Station.objects.get_or_create(
            name="CNR Energies Main Branch",
            defaults={"location": "Kericho, Kenya"},
        )

        pms, _ = FuelProduct.objects.get_or_create(
            code="PMS", defaults={"name": "Super Petrol", "current_price": 195.00}
        )
        ago, _ = FuelProduct.objects.get_or_create(
            code="AGO", defaults={"name": "Diesel", "current_price": 180.00}
        )

        tank_pms, _ = Tank.objects.get_or_create(
            name="Tank 1 - Super Petrol",
            station=station,
            defaults={
                "product": pms,
                "capacity_liters": 30000.00,
                "current_capacity_liters": 22000.00,
            },
        )
        tank_ago, _ = Tank.objects.get_or_create(
            name="Tank 2 - Diesel",
            station=station,
            defaults={
                "product": ago,
                "capacity_liters": 30000.00,
                "current_capacity_liters": 18000.00,
            },
        )

        pump1, _ = Pump.objects.get_or_create(name="Pump 01", station=station)

        nozzle_1a, nozzle_1a_created = Nozzle.objects.get_or_create(
            name="Nozzle 1A", pump=pump1, defaults={"tank": tank_pms, "product": pms}
        )
        nozzle_1b, nozzle_1b_created = Nozzle.objects.get_or_create(
            name="Nozzle 1B", pump=pump1, defaults={"tank": tank_ago, "product": ago}
        )
        for nozzle, was_created in ((nozzle_1a, nozzle_1a_created), (nozzle_1b, nozzle_1b_created)):
            if not was_created and nozzle.product_id != nozzle.tank.product_id:
                self.stdout.write(
                    self.style.WARNING(
                        f"{nozzle.name} exists but product/tank mismatch — not auto-corrected."
                    )
                )

        self.stdout.write(self.style.SUCCESS("Database seeded successfully!"))
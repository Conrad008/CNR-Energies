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
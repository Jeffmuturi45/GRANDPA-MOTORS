"""
Management command: setup_admin
Creates/updates superuser and seeds initial vehicle & analytics data if database is empty.
Ideal for environments without interactive shell access (like Render free tier).
"""
import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.core.management import call_command
from vehicles.models import Vehicle

User = get_user_model()


class Command(BaseCommand):
    help = "Sets up default superuser and seeds demo data on deployment"

    def handle(self, *args, **options):
        username = os.environ.get("DJANGO_SUPERUSER_USERNAME", "admin")
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL",
                               "admin@grandpamotors.co.ke")
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "1234admin")

        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                "email": email,
                "is_staff": True,
                "is_superuser": True,
            },
        )
        if created:
            user.set_password(password)
            user.save()
            self.stdout.write(self.style.SUCCESS(
                f"Superuser '{username}' created successfully."))
        else:
            if os.environ.get("DJANGO_SUPERUSER_PASSWORD"):
                user.set_password(password)
                user.is_staff = True
                user.is_superuser = True
                user.save()
                self.stdout.write(self.style.SUCCESS(
                    f"Superuser '{username}' credentials updated."))
            else:
                self.stdout.write(self.style.WARNING(
                    f"Superuser '{username}' already exists."))

        # Automatically seed demo data if database has no vehicles
        if Vehicle.objects.count() == 0:
            self.stdout.write(
                "Database has no vehicles. Seeding demo inventory and analytics data...")
            try:
                call_command("seed_demo_data")
                self.stdout.write(self.style.SUCCESS(
                    "Demo inventory and analytics seeded."))
            except Exception as e:
                self.stdout.write(self.style.ERROR(
                    f"Error seeding demo data: {e}"))
        else:
            self.stdout.write(
                f"Database already contains {Vehicle.objects.count()} vehicles.")

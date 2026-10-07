"""
Management command: seed_demo_data
Creates realistic demo vehicles, categories, makes, and analytics data
so the admin dashboard has rich data to display immediately.

Usage:
    python manage.py seed_demo_data
    python manage.py seed_demo_data --clear   # wipe and reseed
    python manage.py seed_demo_data --analytics-only
"""
import random
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.text import slugify
from django.contrib.auth import get_user_model

User = get_user_model()


# ── Seed data ─────────────────────────────────────────────────────────────────

MAKES_DATA = [
    {"name": "Toyota",     "is_popular": True,  "sort_order": 1},
    {"name": "Nissan",     "is_popular": True,  "sort_order": 2},
    {"name": "Mitsubishi", "is_popular": True,  "sort_order": 3},
    {"name": "Mercedes",   "is_popular": True,  "sort_order": 4},
    {"name": "BMW",        "is_popular": True,  "sort_order": 5},
    {"name": "Isuzu",      "is_popular": True,  "sort_order": 6},
    {"name": "Subaru",     "is_popular": False, "sort_order": 7},
    {"name": "Honda",      "is_popular": False, "sort_order": 8},
    {"name": "Mazda",      "is_popular": False, "sort_order": 9},
    {"name": "Volkswagen", "is_popular": False, "sort_order": 10},
    {"name": "Ford",       "is_popular": False, "sort_order": 11},
    {"name": "Hyundai",    "is_popular": False, "sort_order": 12},
]

MODELS_DATA = {
    "Toyota":     ["Land Cruiser Prado", "Hilux", "RAV4", "Corolla", "Fielder", "Land Cruiser 200", "Vitz", "Alphard"],
    "Nissan":     ["X-Trail", "Navara", "Note", "Juke", "Patrol", "Wingroad", "Tiida"],
    "Mitsubishi": ["Pajero", "L200", "Outlander", "Eclipse Cross", "Galant Fortis"],
    "Mercedes":   ["C-Class", "E-Class", "GLE", "Sprinter", "A-Class"],
    "BMW":        ["3 Series", "5 Series", "X5", "X3", "7 Series"],
    "Isuzu":      ["D-Max", "MU-X", "FRR", "NPR"],
    "Subaru":     ["Forester", "Outback", "Legacy", "Impreza", "XV"],
    "Honda":      ["CR-V", "HR-V", "Fit", "Accord", "Civic"],
    "Mazda":      ["CX-5", "Demio", "Atenza", "CX-3"],
    "Volkswagen": ["Tiguan", "Polo", "Golf", "Passat"],
    "Ford":       ["Ranger", "Explorer", "Everest"],
    "Hyundai":    ["Tucson", "Santa Fe", "i10", "Creta"],
}

CATEGORIES_DATA = [
    {"name": "SUV",            "icon": "🚙", "is_popular": True,  "sort_order": 1},
    {"name": "Sedan",          "icon": "🚗", "is_popular": True,  "sort_order": 2},
    {"name": "Pickup / Truck", "icon": "🛻", "is_popular": True,  "sort_order": 3},
    {"name": "Hatchback",      "icon": "🚘", "is_popular": True,  "sort_order": 4},
    {"name": "Van / Minivan",  "icon": "🚐", "is_popular": True,  "sort_order": 5},
    {"name": "Station Wagon",  "icon": "🚖", "is_popular": False, "sort_order": 6},
    {"name": "Bus / Matatu",   "icon": "🚌", "is_popular": False, "sort_order": 7},
    {"name": "Commercial",     "icon": "🚛", "is_popular": False, "sort_order": 8},
]

CATEGORY_MAP = {
    "Land Cruiser Prado": "SUV",        "X-Trail": "SUV",
    "RAV4": "SUV",                       "Pajero": "SUV",
    "Land Cruiser 200": "SUV",           "Patrol": "SUV",
    "Outlander": "SUV",                  "Forester": "SUV",
    "CR-V": "SUV",                       "CX-5": "SUV",
    "Tiguan": "SUV",                     "MU-X": "SUV",
    "GLE": "SUV",                        "X5": "SUV",
    "HR-V": "SUV",                       "Tucson": "SUV",
    "Santa Fe": "SUV",                   "Juke": "SUV",
    "Subaru XV": "SUV",                  "Eclipse Cross": "SUV",
    "Hilux": "Pickup / Truck",           "Navara": "Pickup / Truck",
    "L200": "Pickup / Truck",            "D-Max": "Pickup / Truck",
    "Ranger": "Pickup / Truck",
    "Corolla": "Sedan",                  "C-Class": "Sedan",
    "E-Class": "Sedan",                  "3 Series": "Sedan",
    "5 Series": "Sedan",                 "7 Series": "Sedan",
    "Galant Fortis": "Sedan",           "Accord": "Sedan",
    "Atenza": "Sedan",                   "Passat": "Sedan",
    "Legacy": "Sedan",                   "Tiida": "Sedan",
    "Vitz": "Hatchback",                 "Note": "Hatchback",
    "Fit": "Hatchback",                  "Demio": "Hatchback",
    "Polo": "Hatchback",                 "Golf": "Hatchback",
    "Civic": "Hatchback",               "A-Class": "Hatchback",
    "i10": "Hatchback",                  "Impreza": "Hatchback",
    "Creta": "Hatchback",
    "Fielder": "Station Wagon",          "Wingroad": "Station Wagon",
    "Outback": "Station Wagon",
    "Alphard": "Van / Minivan",          "Sprinter": "Van / Minivan",
    "FRR": "Commercial",                 "NPR": "Commercial",
    "Explorer": "SUV",                   "Everest": "SUV",
    "X3": "SUV",                         "CX-3": "SUV",
}

COLORS = [
    "Pearl White", "Metallic Silver", "Jet Black", "Graphite Grey",
    "Deep Blue", "Wine Red", "Champagne Gold", "Forest Green",
    "Sandy Beige", "Titanium Bronze",
]

CONDITIONS = ["FOREIGN_USED", "FOREIGN_USED", "FOREIGN_USED", "LOCALLY_USED", "NEW"]
FUEL_TYPES  = ["PETROL", "PETROL", "DIESEL", "DIESEL", "HYBRID"]
TRANSMISSIONS = ["AUTOMATIC", "AUTOMATIC", "MANUAL", "CVT"]
DRIVETRAINS   = ["FWD", "FWD", "AWD", "4WD", "RWD"]


class Command(BaseCommand):
    help = "Seed demo vehicles, makes, categories, and analytics data"

    def add_arguments(self, parser):
        parser.add_argument("--clear",           action="store_true", help="Delete all vehicles first")
        parser.add_argument("--analytics-only",  action="store_true", help="Only seed analytics data")
        parser.add_argument("--count",  type=int, default=50,         help="Number of vehicles (default 50)")

    def handle(self, *args, **options):
        if options["analytics_only"]:
            self._seed_analytics()
            return

        if options["clear"]:
            self._clear()

        self._seed_makes_categories()
        self._seed_vehicles(options["count"])
        self._seed_analytics()
        self.stdout.write(self.style.SUCCESS("[OK] Demo data seeded successfully!"))

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _clear(self):
        from vehicles.models import Vehicle, Make, Category, VehicleModel
        from analytics.models import PageView, DailyStat, VehicleView, TopVehicleStat
        self.stdout.write("Clearing existing data...")
        TopVehicleStat.objects.all().delete()
        VehicleView.objects.all().delete()
        DailyStat.objects.all().delete()
        PageView.objects.all().delete()
        Vehicle.objects.all().delete()
        VehicleModel.objects.all().delete()
        Make.objects.all().delete()
        Category.objects.all().delete()
        self.stdout.write(self.style.WARNING("  Cleared."))

    def _seed_makes_categories(self):
        from vehicles.models import Make, Category, VehicleModel
        self.stdout.write("Seeding makes, models, categories...")

        cats = {}
        for cd in CATEGORIES_DATA:
            try:
                cat, created = Category.objects.get_or_create(
                    name=cd["name"],
                    defaults=dict(
                        slug=slugify(cd["name"]),
                        icon=cd["icon"],
                        is_popular=cd["is_popular"],
                        sort_order=cd["sort_order"],
                    ),
                )
                if not created:
                    # Update popular/sort on existing
                    Category.objects.filter(pk=cat.pk).update(
                        is_popular=cd["is_popular"], sort_order=cd["sort_order"]
                    )
            except Exception:
                cat = Category.objects.filter(name=cd["name"]).first()
            if cat:
                cats[cd["name"]] = cat

        for md in MAKES_DATA:
            try:
                make, created = Make.objects.get_or_create(
                    name=md["name"],
                    defaults=dict(
                        slug=slugify(md["name"]),
                        is_popular=md["is_popular"],
                        sort_order=md["sort_order"],
                    ),
                )
                if not created:
                    Make.objects.filter(pk=make.pk).update(
                        is_popular=md["is_popular"], sort_order=md["sort_order"]
                    )
            except Exception:
                make = Make.objects.filter(name=md["name"]).first()
            if not make:
                continue
            for model_name in MODELS_DATA.get(md["name"], []):
                try:
                    VehicleModel.objects.get_or_create(
                        make=make,
                        name=model_name,
                        defaults=dict(slug=slugify(model_name)),
                    )
                except Exception:
                    pass

        self.stdout.write(self.style.SUCCESS(f"  [OK] {Make.objects.count()} makes, {Category.objects.count()} categories"))

    def _seed_vehicles(self, count: int):
        from vehicles.models import (
            Vehicle, Make, Category, VehicleModel,
            VehicleStatus, PricingType,
        )
        self.stdout.write(f"Seeding {count} vehicles...")
        now = timezone.now()
        created = 0

        makes_qs      = list(Make.objects.prefetch_related("models").all())
        categories_qs = list(Category.objects.all())
        if not makes_qs or not categories_qs:
            self.stdout.write(self.style.ERROR("No makes or categories found!"))
            return

        for i in range(count):
            make        = random.choice(makes_qs)
            models_list = list(make.models.all())
            if not models_list:
                continue
            model  = random.choice(models_list)
            year   = random.randint(2016, 2024)
            color  = random.choice(COLORS)
            cond   = random.choice(CONDITIONS)
            fuel   = random.choice(FUEL_TYPES)
            trans  = random.choice(TRANSMISSIONS)
            drive  = random.choice(DRIVETRAINS)

            # Category lookup
            cat_name = CATEGORY_MAP.get(model.name, "SUV")
            cat = next((c for c in categories_qs if c.name == cat_name), categories_qs[0])

            # Price range by make prestige
            if make.name in ("Mercedes", "BMW", "Land Cruiser 200", "Patrol"):
                price = Decimal(random.randint(35, 120) * 100_000)
            elif make.name in ("Toyota", "Mitsubishi", "Subaru"):
                price = Decimal(random.randint(15, 60) * 100_000)
            else:
                price = Decimal(random.randint(8, 35) * 100_000)

            mileage = random.randint(15_000, 180_000) if cond != "NEW" else random.randint(0, 500)

            # Status distribution: 70% available, 15% reserved, 10% sold, 5% archived
            rand_status = random.random()
            if rand_status < 0.70:
                status = VehicleStatus.AVAILABLE
            elif rand_status < 0.85:
                status = VehicleStatus.RESERVED
            elif rand_status < 0.95:
                status = VehicleStatus.SOLD
            else:
                status = VehicleStatus.ARCHIVED

            is_published  = status != VehicleStatus.ARCHIVED
            featured      = random.random() < 0.20 and status == VehicleStatus.AVAILABLE
            new_arrival   = random.random() < 0.25 and status == VehicleStatus.AVAILABLE

            days_ago      = random.randint(0, 180)
            published_at  = now - timedelta(days=days_ago)

            view_count    = random.randint(0, 2000) if is_published else 0
            inquiry_count = random.randint(0, int(view_count * 0.08)) if view_count else 0

            slug_base = slugify(f"{year}-{make.name}-{model.name}-{color}")
            slug      = f"{slug_base}-{i}"

            try:
                vehicle = Vehicle(
                    make=make,
                    model=model,
                    category=cat,
                    year=year,
                    slug=slug,
                    exterior_color=color,
                    condition=cond,
                    fuel_type=fuel,
                    transmission=trans,
                    drivetrain=drive,
                    price=price,
                    pricing_type=PricingType.NEGOTIABLE if random.random() < 0.3 else PricingType.FIXED,
                    mileage=mileage,
                    engine_capacity=random.choice([1500, 2000, 2400, 2700, 3000, 3500, 4000]),
                    status=status,
                    is_published=is_published,
                    featured=featured,
                    new_arrival=new_arrival,
                    published_at=published_at,
                    view_count=view_count,
                    inquiry_count=inquiry_count,
                    description=(
                        f"This {year} {make.name} {model.name} is in excellent condition. "
                        f"Finished in {color}, equipped with a responsive {fuel.lower()} engine "
                        f"and {trans.lower()} transmission. "
                        f"Mileage: {mileage:,} km. Available at Grandpa Motors, Nairobi."
                    ),
                )
                vehicle.save()
                created += 1
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"  Skip vehicle {i}: {e}"))

        self.stdout.write(self.style.SUCCESS(f"  [OK] {created} vehicles created"))

    def _seed_analytics(self):
        from analytics.models import PageView, DailyStat, VehicleView, TopVehicleStat
        from vehicles.models import Vehicle
        self.stdout.write("Seeding analytics data (90 days)...")

        now     = timezone.now()
        vehicles = list(Vehicle.objects.filter(is_published=True)[:30])
        paths   = ["/", "/vehicles/", "/catalogue/", "/about/", "/contact/"]

        BROWSERS     = ["Chrome", "Firefox", "Safari", "Edge"]
        DEVICES      = ["desktop", "desktop", "mobile", "mobile", "tablet"]
        OS_LIST      = ["Windows", "Android", "iOS", "macOS", "Linux"]
        REFERERS     = ["https://google.com", "https://facebook.com", "https://twitter.com",
                        "", "", "", ""]  # empty = direct

        # Build 90 days of DailyStat and a sample of PageViews
        for days_ago in range(90, 0, -1):
            day          = (now - timedelta(days=days_ago)).date()
            # Simulate growth trend: older days have fewer views
            base_views   = random.randint(20, 50) + int((90 - days_ago) * 1.5)
            weekday_mult = 1.4 if day.weekday() < 5 else 0.7
            total_views  = int(base_views * weekday_mult)
            unique_sess  = int(total_views * random.uniform(0.55, 0.75))
            veh_views    = int(total_views * random.uniform(0.30, 0.55))
            mobile       = int(total_views * random.uniform(0.40, 0.60))
            desktop      = int(total_views * random.uniform(0.30, 0.50))
            tablet       = total_views - mobile - desktop

            DailyStat.objects.update_or_create(
                date=day,
                defaults=dict(
                    total_views=total_views,
                    unique_sessions=unique_sess,
                    vehicle_page_views=veh_views,
                    mobile_views=max(0, mobile),
                    desktop_views=max(0, desktop),
                    tablet_views=max(0, tablet),
                    top_paths=[{"path": p, "count": random.randint(5, 80)} for p in paths],
                    top_referers=[{"referer": r, "count": random.randint(3, 40)}
                                  for r in REFERERS if r],
                ),
            )

            # Top vehicle stats for this day
            if vehicles:
                shuffled = vehicles[:]
                random.shuffle(shuffled)
                for rank, v in enumerate(shuffled[:10], 1):
                    vc = random.randint(1, max(1, veh_views // len(shuffled)))
                    TopVehicleStat.objects.update_or_create(
                        date=day,
                        vehicle=v,
                        defaults=dict(view_count=vc, rank=rank, inquiry_count=random.randint(0, max(1, vc // 8))),
                    )

        self.stdout.write(self.style.SUCCESS(f"  [OK] Analytics seeded for 90 days"))

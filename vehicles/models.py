import uuid
from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.utils.text import slugify
from django.urls import reverse
from core.utils import generate_vehicle_image_path, validate_image_upload


# ─────────────────────────────────────────────
# CHOICE CONSTANTS
# ─────────────────────────────────────────────

class VehicleStatus(models.TextChoices):
    AVAILABLE = "AVAILABLE", "Available"
    RESERVED = "RESERVED",  "Reserved"
    SOLD = "SOLD",      "Sold"
    ARCHIVED = "ARCHIVED",  "Archived"


class VehicleCondition(models.TextChoices):
    NEW = "NEW",            "New"
    FOREIGN_USED = "FOREIGN_USED",   "Foreign Used"
    LOCALLY_USED = "LOCALLY_USED",   "Locally Used"
    RECONDITIONED = "RECONDITIONED",  "Reconditioned"


class PricingType(models.TextChoices):
    FIXED = "FIXED",            "Fixed Price"
    NEGOTIABLE = "NEGOTIABLE",       "Negotiable"
    PRICE_ON_REQUEST = "PRICE_ON_REQUEST", "Price on Request"


class FuelType(models.TextChoices):
    PETROL = "PETROL",   "Petrol"
    DIESEL = "DIESEL",   "Diesel"
    HYBRID = "HYBRID",   "Hybrid"
    ELECTRIC = "ELECTRIC", "Electric"
    PLUGIN = "PLUGIN",   "Plug-in Hybrid"
    LPG = "LPG",      "LPG"
    CNG = "CNG",      "CNG"


class Transmission(models.TextChoices):
    AUTOMATIC = "AUTOMATIC", "Automatic"
    MANUAL = "MANUAL",    "Manual"
    CVT = "CVT",       "CVT"
    DCT = "DCT",       "Dual-Clutch (DCT)"
    SEMI_AUTO = "SEMI_AUTO", "Semi-Automatic"


class Drivetrain(models.TextChoices):
    FWD = "FWD", "Front-Wheel Drive (FWD)"
    RWD = "RWD", "Rear-Wheel Drive (RWD)"
    AWD = "AWD", "All-Wheel Drive (AWD)"
    FOUR_WD = "4WD", "Four-Wheel Drive (4WD)"


class BodyType(models.TextChoices):
    SEDAN = "SEDAN",       "Sedan"
    SUV = "SUV",         "SUV"
    HATCHBACK = "HATCHBACK",   "Hatchback"
    PICKUP = "PICKUP",      "Pickup / Truck"
    VAN = "VAN",         "Van / Minivan"
    COUPE = "COUPE",       "Coupe"
    CONVERTIBLE = "CONVERTIBLE", "Convertible"
    WAGON = "WAGON",       "Station Wagon"
    BUS = "BUS",         "Bus / Matatu"
    TRUCK = "TRUCK",       "Truck / Lorry"
    OTHER = "OTHER",       "Other"


# Documentation choices
class LogbookStatus(models.TextChoices):
    AVAILABLE = "AVAILABLE",     "Available"
    PROCESSING = "PROCESSING",    "Processing"
    NOT_AVAILABLE = "NOT_AVAILABLE", "Not Available"


class DutyStatus(models.TextChoices):
    PAID = "PAID",           "Paid"
    PROCESSING = "PROCESSING",     "Processing"
    NOT_PAID = "NOT_PAID",       "Not Paid"
    NOT_APPLICABLE = "NOT_APPLICABLE", "Not Applicable"


class TransferStatus(models.TextChoices):
    READY = "READY",      "Ready"
    PROCESSING = "PROCESSING", "Processing"
    NOT_READY = "NOT_READY",  "Not Ready"


class InspectionStatus(models.TextChoices):
    COMPLETED = "COMPLETED",     "Completed"
    PENDING = "PENDING",       "Pending"
    NOT_INSPECTED = "NOT_INSPECTED", "Not Inspected"


class DocumentVerification(models.TextChoices):
    VERIFIED = "VERIFIED",     "Verified"
    PENDING = "PENDING",      "Pending"
    NOT_VERIFIED = "NOT_VERIFIED", "Not Verified"


class MileageVerification(models.TextChoices):
    VERIFIED = "VERIFIED",     "Verified"
    UNVERIFIED = "UNVERIFIED",   "Unverified"


# ─────────────────────────────────────────────
# MAKE / MODEL / CATEGORY — lookup tables
# ─────────────────────────────────────────────

class Make(models.Model):
    """Vehicle manufacturer — Toyota, BMW, Mercedes, etc."""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    logo = models.ImageField(upload_to="makes/logos/", blank=True, null=True)
    description = models.TextField(blank=True)
    is_popular = models.BooleanField(default=False, db_index=True)
    sort_order = models.PositiveSmallIntegerField(default=0, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Make"
        verbose_name_plural = "Makes"
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["is_popular", "sort_order"]),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("catalogue:by_make", kwargs={"make_slug": self.slug})


class VehicleModel(models.Model):
    """
    Vehicle model — Prado, X5, C-Class, etc.
    Scoped to a Make.
    """
    make = models.ForeignKey(
        Make, on_delete=models.CASCADE, related_name="models")
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["make__name", "name"]
        unique_together = [("make", "name")]
        verbose_name = "Model"
        verbose_name_plural = "Models"
        indexes = [
            models.Index(fields=["make", "slug"]),
            models.Index(fields=["slug"]),
        ]

    def __str__(self):
        return f"{self.make.name} {self.name}"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse(
            "catalogue:by_model",
            kwargs={"make_slug": self.make.slug, "model_slug": self.slug},
        )


class Category(models.Model):
    """
    High-level vehicle category — SUV, Sedan, Pickup, etc.
    Separate from BodyType to allow custom groupings.
    """
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    icon = models.CharField(max_length=50, blank=True,
                            help_text="CSS class or emoji")
    image = models.ImageField(upload_to="categories/", blank=True, null=True)
    description = models.TextField(blank=True)
    is_popular = models.BooleanField(default=False, db_index=True)
    sort_order = models.PositiveSmallIntegerField(default=0, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["is_popular", "sort_order"]),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("catalogue:by_category", kwargs={"category_slug": self.slug})


class Feature(models.Model):
    """
    Structured vehicle feature — Sunroof, CarPlay, etc.
    Admin manages the master list; vehicles reference it.
    """
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    icon = models.CharField(max_length=50, blank=True)
    category = models.CharField(
        max_length=50, blank=True,
        help_text="Group label e.g. Safety, Comfort, Technology"
    )
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["category", "sort_order", "name"]
        verbose_name = "Feature"
        verbose_name_plural = "Features"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


# ─────────────────────────────────────────────
# CORE VEHICLE MODEL
# ─────────────────────────────────────────────

class Vehicle(models.Model):
    """
    Central vehicle record — single source of truth.
    All public pages must derive data from this model.
    """

    # Identity
    uuid = models.UUIDField(default=uuid.uuid4, unique=True,
                            editable=False, db_index=True)
    stock_number = models.CharField(
        max_length=50, unique=True, blank=True,
        help_text="Auto-generated if left blank e.g. VEH-1024"
    )

    # Classification
    make = models.ForeignKey(
        Make, on_delete=models.PROTECT, related_name="vehicles")
    model = models.ForeignKey(
        VehicleModel, on_delete=models.PROTECT, related_name="vehicles")
    variant = models.CharField(
        max_length=100, blank=True, help_text="Trim/grade e.g. TX-L, Sport")
    year = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1900), MaxValueValidator(2100)],
        db_index=True,
    )
    condition = models.CharField(
        max_length=20, choices=VehicleCondition.choices, db_index=True)
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="vehicles"
    )
    body_type = models.CharField(
        max_length=20, choices=BodyType.choices, blank=True, db_index=True)

    # Pricing
    price = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal("0"))],
        db_index=True,
        help_text="Price in KES. Leave blank for Price on Request."
    )
    previous_price = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal("0"))],
        help_text="Previous price — shown as 'Was KSh X' if set"
    )
    pricing_type = models.CharField(
        max_length=20, choices=PricingType.choices,
        default=PricingType.NEGOTIABLE, db_index=True
    )
    currency = models.CharField(max_length=3, default="KES")

    # Specifications
    mileage = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Mileage in km", db_index=True
    )
    fuel_type = models.CharField(
        max_length=20, choices=FuelType.choices, blank=True, db_index=True
    )
    transmission = models.CharField(
        max_length=20, choices=Transmission.choices, blank=True, db_index=True
    )
    drivetrain = models.CharField(
        max_length=10, choices=Drivetrain.choices, blank=True, db_index=True
    )
    engine_capacity = models.DecimalField(
        max_digits=5, decimal_places=1, null=True, blank=True,
        help_text="Engine displacement in litres e.g. 2.8"
    )
    engine_power = models.PositiveSmallIntegerField(
        null=True, blank=True, help_text="Power in horsepower (hp)"
    )
    exterior_color = models.CharField(max_length=80, blank=True)
    interior_color = models.CharField(max_length=80, blank=True)

    # Content
    description = models.TextField(blank=True)
    location = models.CharField(max_length=150, blank=True, db_index=True)

    # Features (M2M)
    features = models.ManyToManyField(
        Feature, blank=True, related_name="vehicles")

    # Flags
    status = models.CharField(
        max_length=20, choices=VehicleStatus.choices,
        default=VehicleStatus.AVAILABLE, db_index=True
    )
    featured = models.BooleanField(default=False, db_index=True)
    new_arrival = models.BooleanField(default=False, db_index=True)

    # Publishing
    is_published = models.BooleanField(default=False, db_index=True)
    published_at = models.DateTimeField(null=True, blank=True, db_index=True)

    # Analytics (denormalized counters — updated by Celery)
    view_count = models.PositiveIntegerField(default=0, db_index=True)
    inquiry_count = models.PositiveIntegerField(default=0, db_index=True)

    # SEO
    seo_title = models.CharField(max_length=70, blank=True)
    seo_description = models.CharField(max_length=160, blank=True)
    slug = models.SlugField(max_length=200, unique=True,
                            blank=True, db_index=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-published_at", "-created_at"]
        verbose_name = "Vehicle"
        verbose_name_plural = "Vehicles"
        indexes = [
            # Composite indexes for common catalogue queries
            models.Index(fields=["is_published", "status"],
                         name="idx_pub_status"),
            models.Index(fields=["is_published", "featured"],
                         name="idx_pub_featured"),
            models.Index(
                fields=["is_published", "new_arrival"], name="idx_pub_arrival"),
            models.Index(fields=["is_published", "status",
                         "price"], name="idx_pub_status_price"),
            models.Index(fields=["is_published", "status",
                         "year"], name="idx_pub_status_year"),
            models.Index(fields=["is_published", "status",
                         "mileage"], name="idx_pub_status_mile"),
            models.Index(fields=["make", "model", "year"],
                         name="idx_make_model_year"),
            models.Index(fields=["published_at"], name="idx_published_at"),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(price__gte=0),
                name="price_non_negative",
            ),
            models.CheckConstraint(
                check=models.Q(previous_price__gte=0) | models.Q(
                    previous_price__isnull=True),
                name="previous_price_non_negative",
            ),
            models.CheckConstraint(
                check=models.Q(year__gte=1900) & models.Q(year__lte=2100),
                name="year_valid_range",
            ),
        ]

    def __str__(self):
        return f"{self.year} {self.make} {self.model} {self.variant}".strip()

    def save(self, *args, **kwargs):
        # Auto-generate slug
        if not self.slug:
            base = f"{self.year}-{self.make.name}-{self.model.name}"
            if self.variant:
                base += f"-{self.variant}"
            self.slug = slugify(base)
            # Ensure uniqueness
            original_slug = self.slug
            counter = 1
            while Vehicle.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{original_slug}-{counter}"
                counter += 1

        # Auto-generate stock number
        if not self.stock_number:
            pass  # Set after first save — see below

        # Set published_at on first publish
        if self.is_published and not self.published_at:
            self.published_at = timezone.now()
        elif not self.is_published:
            self.published_at = None

        super().save(*args, **kwargs)

        # Stock number requires PK
        if not self.stock_number:
            self.stock_number = f"VEH-{self.pk:04d}"
            Vehicle.objects.filter(pk=self.pk).update(
                stock_number=self.stock_number)

    def get_absolute_url(self):
        return reverse("vehicles:detail", kwargs={"slug": self.slug})

    # ── Convenience properties ──────────────────

    @property
    def title(self) -> str:
        parts = [str(self.year), self.make.name, self.model.name]
        if self.variant:
            parts.append(self.variant)
        return " ".join(parts)

    @property
    def primary_image(self):
        """Return the primary image object, or None."""
        return self.images.filter(is_primary=True).first() or self.images.first()

    DEFAULT_MAKE_IMAGES = {
        "Toyota": "https://images.unsplash.com/photo-1621007947382-bb3c3994e3fb?auto=format&fit=crop&w=1200&q=80",
        "Mercedes": "https://images.unsplash.com/photo-1618843479313-40f8afb4b4d8?auto=format&fit=crop&w=1200&q=80",
        "BMW": "https://images.unsplash.com/photo-1555215695-3004980ad54e?auto=format&fit=crop&w=1200&q=80",
        "Subaru": "https://images.unsplash.com/photo-1580273916550-e323be2ae537?auto=format&fit=crop&w=1200&q=80",
        "Nissan": "https://images.unsplash.com/photo-1590362891991-f776e747a588?auto=format&fit=crop&w=1200&q=80",
        "Mitsubishi": "https://images.unsplash.com/photo-1542282088-72c9c27ed0cd?auto=format&fit=crop&w=1200&q=80",
        "Isuzu": "https://images.unsplash.com/photo-1559416523-140ddc3d238c?auto=format&fit=crop&w=1200&q=80",
        "Volkswagen": "https://images.unsplash.com/photo-1541899481282-d53bffe3c35d?auto=format&fit=crop&w=1200&q=80",
        "Honda": "https://images.unsplash.com/photo-1617469767053-d3b523a0b982?auto=format&fit=crop&w=1200&q=80",
        "Ford": "https://images.unsplash.com/photo-1551830820-330a71b99659?auto=format&fit=crop&w=1200&q=80",
        "Mazda": "https://images.unsplash.com/photo-1544829099-b9a0c07fad1a?auto=format&fit=crop&w=1200&q=80",
        "Hyundai": "https://images.unsplash.com/photo-1508974239320-0a029497e820?auto=format&fit=crop&w=1200&q=80",
    }

    DEFAULT_CATEGORY_IMAGES = {
        "SUV": "https://images.unsplash.com/photo-1533473359331-0135ef1b58bf?auto=format&fit=crop&w=1200&q=80",
        "Sedan": "https://images.unsplash.com/photo-1552519507-da3b142c6e3d?auto=format&fit=crop&w=1200&q=80",
        "Pickup / Truck": "https://images.unsplash.com/photo-1559416523-140ddc3d238c?auto=format&fit=crop&w=1200&q=80",
        "Hatchback": "https://images.unsplash.com/photo-1541899481282-d53bffe3c35d?auto=format&fit=crop&w=1200&q=80",
        "Van / Minivan": "https://images.unsplash.com/photo-1570737543098-0983d88f796d?auto=format&fit=crop&w=1200&q=80",
        "Station Wagon": "https://images.unsplash.com/photo-1503376780353-7e6692767b70?auto=format&fit=crop&w=1200&q=80",
        "Commercial": "https://images.unsplash.com/photo-1601584115197-04ecc0da31d7?auto=format&fit=crop&w=1200&q=80",
    }

    @property
    def get_default_image_url(self) -> str:
        """Returns a high-quality realistic vehicle photo based on make or category."""
        if self.make_id and self.make.name in self.DEFAULT_MAKE_IMAGES:
            return self.DEFAULT_MAKE_IMAGES[self.make.name]
        if self.category_id and self.category.name in self.DEFAULT_CATEGORY_IMAGES:
            return self.DEFAULT_CATEGORY_IMAGES[self.category.name]
        return "https://images.unsplash.com/photo-1533473359331-0135ef1b58bf?auto=format&fit=crop&w=1200&q=80"

    @property
    def primary_image_url(self) -> str:
        img = self.primary_image
        if img and img.image:
            try:
                return img.image.url
            except Exception:
                pass
        return self.get_default_image_url

    @property
    def display_gallery_urls(self) -> list[str]:
        """Returns uploaded image URLs or a set of multi-angle photos for the detail gallery."""
        urls = []
        for img in self.images.all():
            if img.image:
                try:
                    urls.append(img.image.url)
                except Exception:
                    pass
        if urls:
            return urls
        base = self.get_default_image_url
        interior = "https://images.unsplash.com/photo-1563720223185-11003d516935?auto=format&fit=crop&w=1200&q=80"
        cockpit = "https://images.unsplash.com/photo-1502877338535-766e1452684a?auto=format&fit=crop&w=1200&q=80"
        return [base, interior, cockpit]


    @property
    def is_price_reduced(self) -> bool:
        return bool(
            self.previous_price
            and self.price
            and self.previous_price > self.price
        )

    @property
    def price_reduction_amount(self):
        if self.is_price_reduced:
            return self.previous_price - self.price
        return None

    @property
    def is_available(self) -> bool:
        return self.status == VehicleStatus.AVAILABLE

    @property
    def display_price(self) -> str:
        if self.pricing_type == PricingType.PRICE_ON_REQUEST or not self.price:
            return "Price on Request"
        return f"KSh {self.price:,.0f}"

    def get_whatsapp_message(self, site_url: str = "") -> str:
        """Generate the WhatsApp inquiry message for this vehicle."""
        lines = [
            f"Hello, I am interested in the {self.title}",
        ]
        if self.price and self.pricing_type != PricingType.PRICE_ON_REQUEST:
            price_str = f"KSh {self.price:,.0f}"
            if self.pricing_type == PricingType.NEGOTIABLE:
                price_str += " (Negotiable)"
            lines[0] += f" listed at {price_str}."
        else:
            lines[0] += "."

        lines.append(f"\nVehicle reference: {self.stock_number}")

        if site_url:
            url = f"{site_url}{self.get_absolute_url()}"
            lines.append(f"\nVehicle link: {url}")

        lines.append(
            "\nI would like to know if it is still available "
            "and confirm the documentation status."
        )
        return "\n".join(lines)

    def get_seo_title(self) -> str:
        if self.seo_title:
            return self.seo_title
        from django.conf import settings
        return f"{self.title} for Sale in Kenya | {settings.DEALERSHIP_NAME}"

    def get_seo_description(self) -> str:
        if self.seo_description:
            return self.seo_description
        parts = []
        if self.mileage:
            parts.append(f"{self.mileage:,} km")
        if self.fuel_type:
            parts.append(self.get_fuel_type_display())
        if self.transmission:
            parts.append(self.get_transmission_display())
        spec_str = " • ".join(parts)
        desc = f"{self.title}."
        if spec_str:
            desc += f" {spec_str}."
        if self.price:
            desc += f" KSh {self.price:,.0f}."
        return desc[:160]


# ─────────────────────────────────────────────
# VEHICLE IMAGES
# ─────────────────────────────────────────────

class VehicleImage(models.Model):
    """
    Vehicle photo. Supports multiple images, ordering, primary flag.
    Images are re-encoded server-side (never trust original).
    """
    vehicle = models.ForeignKey(
        Vehicle, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(
        upload_to=generate_vehicle_image_path,
        validators=[validate_image_upload],
    )
    # Processed/optimized variants (generated by Celery after upload)
    thumbnail = models.ImageField(upload_to="vehicles/thumbs/", blank=True)
    webp_image = models.ImageField(upload_to="vehicles/webp/", blank=True)

    caption = models.CharField(max_length=200, blank=True)
    alt_text = models.CharField(
        max_length=200, blank=True,
        help_text="Descriptive alt text for accessibility and SEO"
    )
    is_primary = models.BooleanField(default=False, db_index=True)
    sort_order = models.PositiveSmallIntegerField(default=0, db_index=True)

    # Metadata
    width = models.PositiveSmallIntegerField(null=True, blank=True)
    height = models.PositiveSmallIntegerField(null=True, blank=True)
    file_size = models.PositiveIntegerField(
        null=True, blank=True, help_text="bytes")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "created_at"]
        verbose_name = "Vehicle Image"
        verbose_name_plural = "Vehicle Images"
        indexes = [
            models.Index(fields=["vehicle", "is_primary"]),
            models.Index(fields=["vehicle", "sort_order"]),
        ]

    def __str__(self):
        return f"{self.vehicle} — Image {self.sort_order}"

    def save(self, *args, **kwargs):
        # Enforce single primary image per vehicle
        if self.is_primary:
            VehicleImage.objects.filter(
                vehicle=self.vehicle, is_primary=True
            ).exclude(pk=self.pk).update(is_primary=False)
        # Auto alt text
        if not self.alt_text and self.vehicle_id:
            try:
                self.alt_text = str(self.vehicle)
            except Exception:
                pass
        super().save(*args, **kwargs)


# ─────────────────────────────────────────────
# VEHICLE DOCUMENTATION
# ─────────────────────────────────────────────

class VehicleDocumentation(models.Model):
    """
    Structured documentation status for a vehicle.
    Drives public badges. Private documents are NOT exposed.
    """
    vehicle = models.OneToOneField(
        Vehicle, on_delete=models.CASCADE, related_name="documentation"
    )

    logbook_status = models.CharField(
        max_length=20, choices=LogbookStatus.choices,
        default=LogbookStatus.NOT_AVAILABLE
    )
    import_docs = models.CharField(
        max_length=20, choices=LogbookStatus.choices,
        default=LogbookStatus.NOT_AVAILABLE,
        verbose_name="Import Documents"
    )
    duty_status = models.CharField(
        max_length=20, choices=DutyStatus.choices,
        default=DutyStatus.NOT_APPLICABLE
    )
    transfer_status = models.CharField(
        max_length=20, choices=TransferStatus.choices,
        default=TransferStatus.NOT_READY
    )

    notes = models.TextField(blank=True, help_text="Internal admin notes only")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Vehicle Documentation"
        verbose_name_plural = "Vehicle Documentation"

    def __str__(self):
        return f"Docs — {self.vehicle}"

    # ── Public badge helpers ─────────────────────

    @property
    def is_documents_ready(self) -> bool:
        return (
            self.logbook_status == LogbookStatus.AVAILABLE
            and self.duty_status in (DutyStatus.PAID, DutyStatus.NOT_APPLICABLE)
        )

    @property
    def is_transfer_ready(self) -> bool:
        return self.transfer_status == TransferStatus.READY

    @property
    def is_duty_paid(self) -> bool:
        return self.duty_status == DutyStatus.PAID

    @property
    def public_badges(self) -> list[dict]:
        """Return list of badges to display publicly."""
        badges = []
        if self.is_documents_ready:
            badges.append({"label": "Documents Ready",
                          "style": "green", "icon": "✓"})
        if self.is_duty_paid:
            badges.append({"label": "Duty Paid", "style": "blue", "icon": "✓"})
        if self.is_transfer_ready:
            badges.append({"label": "Transfer Ready",
                          "style": "purple", "icon": "✓"})
        return badges


# ─────────────────────────────────────────────
# VEHICLE VERIFICATION
# ─────────────────────────────────────────────

class VehicleVerification(models.Model):
    """
    Verification status — inspection, mileage, documents.
    Separate from documentation for clarity.
    """
    vehicle = models.OneToOneField(
        Vehicle, on_delete=models.CASCADE, related_name="verification"
    )

    inspection_status = models.CharField(
        max_length=20, choices=InspectionStatus.choices,
        default=InspectionStatus.NOT_INSPECTED
    )
    inspection_date = models.DateField(null=True, blank=True)
    inspection_notes = models.TextField(blank=True, help_text="Internal only")

    mileage_verified = models.CharField(
        max_length=20, choices=MileageVerification.choices,
        default=MileageVerification.UNVERIFIED
    )
    document_verified = models.CharField(
        max_length=20, choices=DocumentVerification.choices,
        default=DocumentVerification.NOT_VERIFIED
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Vehicle Verification"
        verbose_name_plural = "Vehicle Verifications"

    def __str__(self):
        return f"Verification — {self.vehicle}"

    @property
    def is_inspected(self) -> bool:
        return self.inspection_status == InspectionStatus.COMPLETED

    @property
    def is_mileage_verified(self) -> bool:
        return self.mileage_verified == MileageVerification.VERIFIED

    @property
    def is_document_verified(self) -> bool:
        return self.document_verified == DocumentVerification.VERIFIED

    @property
    def public_badges(self) -> list[dict]:
        badges = []
        if self.is_inspected:
            badges.append(
                {"label": "Inspected", "style": "green", "icon": "✓"})
        if self.is_mileage_verified:
            badges.append({"label": "Mileage Verified",
                          "style": "blue", "icon": "✓"})
        if self.is_document_verified:
            badges.append({"label": "Documents Verified",
                          "style": "purple", "icon": "✓"})
        return badges


# ─────────────────────────────────────────────
# PRICE HISTORY
# ─────────────────────────────────────────────

class PriceHistory(models.Model):
    """
    Immutable record of every price change.
    Written automatically when Vehicle.price changes.
    """
    vehicle = models.ForeignKey(
        Vehicle, on_delete=models.CASCADE, related_name="price_history")
    old_price = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True)
    new_price = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True)
    changed_by = models.ForeignKey(
        "auth.User", on_delete=models.SET_NULL, null=True, blank=True
    )
    changed_at = models.DateTimeField(auto_now_add=True, db_index=True)
    note = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["-changed_at"]
        verbose_name = "Price History"
        verbose_name_plural = "Price History"
        indexes = [
            models.Index(fields=["vehicle", "changed_at"]),
        ]

    def __str__(self):
        return f"{self.vehicle} — {self.old_price} → {self.new_price}"

    @property
    def is_reduction(self) -> bool:
        if self.old_price and self.new_price:
            return self.new_price < self.old_price
        return False


# ─────────────────────────────────────────────
# AUDIT LOG
# ─────────────────────────────────────────────

class AuditLog(models.Model):
    """
    Records important admin actions on vehicles.
    Append-only — never delete entries.
    """
    class Action(models.TextChoices):
        CREATED = "CREATED",    "Vehicle Created"
        UPDATED = "UPDATED",    "Vehicle Updated"
        PUBLISHED = "PUBLISHED",  "Published"
        UNPUBLISHED = "UNPUBLISHED", "Unpublished"
        PRICE_CHANGED = "PRICE_CHANGED", "Price Changed"
        FEATURED = "FEATURED",   "Marked as Featured"
        UNFEATURED = "UNFEATURED", "Removed from Featured"
        RESERVED = "RESERVED",   "Marked as Reserved"
        SOLD = "SOLD",       "Marked as Sold"
        ARCHIVED = "ARCHIVED",   "Archived"
        IMAGE_ADDED = "IMAGE_ADDED",   "Image Added"
        IMAGE_REMOVED = "IMAGE_REMOVED", "Image Removed"

    vehicle = models.ForeignKey(
        Vehicle, on_delete=models.CASCADE, related_name="audit_logs", null=True, blank=True
    )
    action = models.CharField(
        max_length=20, choices=Action.choices, db_index=True)
    user = models.ForeignKey(
        "auth.User", on_delete=models.SET_NULL, null=True, blank=True
    )
    detail = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"
        indexes = [
            models.Index(fields=["vehicle", "created_at"]),
            models.Index(fields=["action", "created_at"]),
        ]

    def __str__(self):
        return f"{self.action} — {self.vehicle} at {self.created_at:%Y-%m-%d %H:%M}"

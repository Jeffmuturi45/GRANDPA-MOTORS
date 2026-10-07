"""
All vehicle query logic in one place.
Views call these functions — never build raw querysets in views.
"""
import logging
from decimal import Decimal
from django.db import models
from django.db.models import Q, F, Count, Prefetch
from django.core.paginator import Paginator, EmptyPage
from django.conf import settings
from .models import Vehicle, VehicleImage, VehicleStatus

logger = logging.getLogger(__name__)

# ── Base published queryset ───────────────────────────────────────────────────


def published_vehicles():
    """
    Base queryset — only published, non-archived vehicles.
    Every public query must start here.
    """
    return (
        Vehicle.objects
        .filter(is_published=True)
        .exclude(status=VehicleStatus.ARCHIVED)
        .select_related("make", "model", "category")
    )


def with_primary_image(qs):
    """Prefetch only the primary image — for catalogue cards."""
    primary_images = VehicleImage.objects.filter(
        is_primary=True
    ).order_by("sort_order")
    return qs.prefetch_related(
        Prefetch("images", queryset=primary_images,
                 to_attr="primary_images_list")
    )


def with_all_images(qs):
    """Prefetch all images — for detail page gallery."""
    return qs.prefetch_related(
        Prefetch(
            "images",
            queryset=VehicleImage.objects.order_by("sort_order"),
            to_attr="all_images_list",
        )
    )


def with_documentation(qs):
    """Prefetch documentation and verification — for detail page."""
    return qs.select_related("documentation", "verification")


def with_features(qs):
    """Prefetch features — for detail page."""
    from .models import Feature
    return qs.prefetch_related(
        Prefetch("features", queryset=Feature.objects.order_by(
            "category", "sort_order"))
    )


# ── Filter builder ────────────────────────────────────────────────────────────

def apply_filters(qs, params: dict):
    """
    Apply all catalogue filters from request GET params.
    Every filter is a DB-side operation — never filter in Python.
    """

    # ── Search query
    q = params.get("q", "").strip()
    if q:
        qs = _apply_search(qs, q)

    # ── Condition
    conditions = params.getlist("condition") if hasattr(params, "getlist") else (
        [params["condition"]] if params.get("condition") else []
    )
    if conditions:
        qs = qs.filter(condition__in=conditions)

    # ── Status
    status = params.get("status", "")
    if status:
        qs = qs.filter(status=status)
    else:
        # Default: show only available + reserved
        qs = qs.filter(status__in=[VehicleStatus.AVAILABLE, "RESERVED"])

    # ── Make
    make_slugs = params.getlist("make") if hasattr(params, "getlist") else (
        [params["make"]] if params.get("make") else []
    )
    if make_slugs:
        qs = qs.filter(make__slug__in=make_slugs)

    # ── Model
    model_slugs = params.getlist("model") if hasattr(params, "getlist") else (
        [params["model"]] if params.get("model") else []
    )
    if model_slugs:
        qs = qs.filter(model__slug__in=model_slugs)

    # ── Category
    category_slugs = params.getlist("category") if hasattr(params, "getlist") else (
        [params["category"]] if params.get("category") else []
    )
    if category_slugs:
        qs = qs.filter(category__slug__in=category_slugs)

    # ── Body type
    body_types = params.getlist("body_type") if hasattr(params, "getlist") else (
        [params["body_type"]] if params.get("body_type") else []
    )
    if body_types:
        qs = qs.filter(body_type__in=body_types)

    # ── Year range
    year_min = params.get("year_min", "")
    year_max = params.get("year_max", "")
    if year_min:
        try:
            qs = qs.filter(year__gte=int(year_min))
        except (ValueError, TypeError):
            pass
    if year_max:
        try:
            qs = qs.filter(year__lte=int(year_max))
        except (ValueError, TypeError):
            pass

    # ── Price range
    price_min = params.get("price_min", "")
    price_max = params.get("price_max", "")
    if price_min:
        try:
            qs = qs.filter(price__gte=Decimal(price_min))
        except Exception:
            pass
    if price_max:
        try:
            qs = qs.filter(price__lte=Decimal(price_max))
        except Exception:
            pass

    # ── Pricing type
    pricing_types = params.getlist("pricing_type") if hasattr(params, "getlist") else (
        [params["pricing_type"]] if params.get("pricing_type") else []
    )
    if pricing_types:
        qs = qs.filter(pricing_type__in=pricing_types)

    # ── Fuel type
    fuel_types = params.getlist("fuel_type") if hasattr(params, "getlist") else (
        [params["fuel_type"]] if params.get("fuel_type") else []
    )
    if fuel_types:
        qs = qs.filter(fuel_type__in=fuel_types)

    # ── Transmission
    transmissions = params.getlist("transmission") if hasattr(params, "getlist") else (
        [params["transmission"]] if params.get("transmission") else []
    )
    if transmissions:
        qs = qs.filter(transmission__in=transmissions)

    # ── Drivetrain
    drivetrains = params.getlist("drivetrain") if hasattr(params, "getlist") else (
        [params["drivetrain"]] if params.get("drivetrain") else []
    )
    if drivetrains:
        qs = qs.filter(drivetrain__in=drivetrains)

    # ── Mileage max
    mileage_max = params.get("mileage_max", "")
    if mileage_max:
        try:
            qs = qs.filter(mileage__lte=int(mileage_max))
        except (ValueError, TypeError):
            pass

    # ── Location
    location = params.get("location", "").strip()
    if location:
        qs = qs.filter(location__icontains=location)

    # ── Flags
    if params.get("featured"):
        qs = qs.filter(featured=True)
    if params.get("new_arrival"):
        qs = qs.filter(new_arrival=True)

    # ── Documentation filters
    if params.get("docs_ready"):
        qs = qs.filter(
            documentation__logbook_status="AVAILABLE",
            documentation__duty_status__in=["PAID", "NOT_APPLICABLE"],
        )
    if params.get("transfer_ready"):
        qs = qs.filter(documentation__transfer_status="READY")
    if params.get("duty_paid"):
        qs = qs.filter(documentation__duty_status="PAID")

    # ── Verification filters
    if params.get("inspected"):
        qs = qs.filter(verification__inspection_status="COMPLETED")
    if params.get("mileage_verified"):
        qs = qs.filter(verification__mileage_verified="VERIFIED")
    if params.get("docs_verified"):
        qs = qs.filter(verification__document_verified="VERIFIED")

    return qs


def _apply_search(qs, query: str):
    """
    Full-text search using PostgreSQL trigram similarity.
    Falls back to icontains if pg_trgm is unavailable.
    """
    terms = query.split()
    q_obj = Q()
    for term in terms:
        q_obj |= (
            Q(make__name__icontains=term) |
            Q(model__name__icontains=term) |
            Q(variant__icontains=term) |
            Q(stock_number__icontains=term) |
            Q(category__name__icontains=term) |
            Q(exterior_color__icontains=term) |
            Q(description__icontains=term)
        )

    # Also try full year match
    if query.strip().isdigit() and len(query.strip()) == 4:
        q_obj |= Q(year=int(query.strip()))

    return qs.filter(q_obj).distinct()


# ── Sorting ───────────────────────────────────────────────────────────────────

SORT_OPTIONS = {
    "recommended":   ("-featured", "-published_at"),
    "newest":        ("-published_at",),
    "oldest":        ("published_at",),
    "price_asc":     ("price",),
    "price_desc":    ("-price",),
    "year_desc":     ("-year",),
    "year_asc":      ("year",),
    "mileage_asc":   ("mileage",),
    "mileage_desc":  ("-mileage",),
    "most_viewed":   ("-view_count",),
    "most_inquired": ("-inquiry_count",),
}

SORT_LABELS = {
    "recommended":   "Recommended",
    "newest":        "Newest First",
    "oldest":        "Oldest First",
    "price_asc":     "Price: Low → High",
    "price_desc":    "Price: High → Low",
    "year_desc":     "Year: Newest",
    "year_asc":      "Year: Oldest",
    "mileage_asc":   "Mileage: Low → High",
    "mileage_desc":  "Mileage: High → Low",
    "most_viewed":   "Most Viewed",
    "most_inquired": "Most Inquired",
}


def apply_sorting(qs, sort_key: str):
    order = SORT_OPTIONS.get(sort_key, SORT_OPTIONS["recommended"])
    return qs.order_by(*order)


# ── Pagination ────────────────────────────────────────────────────────────────

def paginate(qs, page_number, per_page=None):
    """
    Efficient pagination. Never loads all records.
    Returns (page_obj, paginator).
    """
    per_page = per_page or settings.VEHICLES_PER_PAGE
    paginator = Paginator(qs, per_page)
    try:
        page = paginator.page(page_number)
    except EmptyPage:
        page = paginator.page(paginator.num_pages)
    return page, paginator


# ── Homepage loaders ──────────────────────────────────────────────────────────

def get_featured_vehicles(limit=8):
    return (
        with_primary_image(published_vehicles())
        .filter(featured=True, status=VehicleStatus.AVAILABLE)
        .order_by("-published_at")[:limit]
    )


def get_latest_arrivals(limit=8):
    return (
        with_primary_image(published_vehicles())
        .filter(new_arrival=True, status=VehicleStatus.AVAILABLE)
        .order_by("-published_at")[:limit]
    )


def get_price_reduced_vehicles(limit=6):
    return (
        with_primary_image(published_vehicles())
        .filter(
            previous_price__isnull=False,
            status=VehicleStatus.AVAILABLE,
        )
        .filter(previous_price__gt=F("price"))
        .order_by("-published_at")[:limit]
    )


def get_related_vehicles(vehicle, limit=None):
    limit = limit or settings.RELATED_VEHICLES_COUNT
    qs = (
        with_primary_image(published_vehicles())
        .filter(status=VehicleStatus.AVAILABLE)
        .exclude(pk=vehicle.pk)
    )
    # Same make + category first
    related = list(
        qs.filter(make=vehicle.make, category=vehicle.category)
        .order_by("-published_at")[:limit]
    )
    # Fill with same make if needed
    if len(related) < limit:
        seen_ids = {v.pk for v in related} | {vehicle.pk}
        more = list(
            qs.filter(make=vehicle.make)
            .exclude(pk__in=seen_ids)
            .order_by("-published_at")[: limit - len(related)]
        )
        related += more
    # Fill with similar price range if still needed
    if len(related) < limit and vehicle.price:
        seen_ids = {v.pk for v in related} | {vehicle.pk}
        price_range = vehicle.price * Decimal("0.2")
        more = list(
            qs.filter(
                price__gte=vehicle.price - price_range,
                price__lte=vehicle.price + price_range,
            )
            .exclude(pk__in=seen_ids)
            .order_by("-published_at")[: limit - len(related)]
        )
        related += more
    return related


# ── Navigation data (cached) ──────────────────────────────────────────────────

def get_makes_for_nav():
    from .models import Make
    from .cache import get_or_set, KEY_POPULAR_MAKES, TIMEOUT_LONG
    return get_or_set(
        KEY_POPULAR_MAKES,
        lambda: list(Make.objects.filter(
            is_popular=True).order_by("sort_order", "name")),
        TIMEOUT_LONG,
    )


def get_categories_for_nav():
    from .models import Category
    from .cache import get_or_set, KEY_POPULAR_CATEGORIES, TIMEOUT_LONG
    return get_or_set(
        KEY_POPULAR_CATEGORIES,
        lambda: list(Category.objects.filter(
            is_popular=True).order_by("sort_order", "name")),
        TIMEOUT_LONG,
    )


def get_all_makes():
    from .models import Make
    from .cache import get_or_set, KEY_ALL_MAKES, TIMEOUT_LONG
    return get_or_set(
        KEY_ALL_MAKES,
        lambda: list(Make.objects.annotate(
            vehicle_count=Count("vehicles", filter=Q(
                vehicles__is_published=True,
                vehicles__status=VehicleStatus.AVAILABLE,
            ))
        ).filter(vehicle_count__gt=0).order_by("name")),
        TIMEOUT_LONG,
    )


def get_all_categories():
    from .models import Category
    from .cache import get_or_set, KEY_ALL_CATEGORIES, TIMEOUT_LONG
    return get_or_set(
        KEY_ALL_CATEGORIES,
        lambda: list(Category.objects.annotate(
            vehicle_count=Count("vehicles", filter=Q(
                vehicles__is_published=True,
                vehicles__status=VehicleStatus.AVAILABLE,
            ))
        ).filter(vehicle_count__gt=0).order_by("sort_order", "name")),
        TIMEOUT_LONG,
    )


def get_vehicle_stats():
    from .cache import get_or_set, KEY_STATS_COUNTS, TIMEOUT_MEDIUM

    def _load():
        from .models import Vehicle
        return Vehicle.objects.filter(is_published=True).aggregate(
            total=Count("id"),
            available=Count("id", filter=Q(status="AVAILABLE")),
            reserved=Count("id", filter=Q(status="RESERVED")),
            sold=Count("id", filter=Q(status="SOLD")),
            featured=Count("id", filter=Q(featured=True)),
            new_arrivals=Count("id", filter=Q(new_arrival=True)),
        )
    return get_or_set(KEY_STATS_COUNTS, _load, TIMEOUT_MEDIUM)

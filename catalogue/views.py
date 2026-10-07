import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.conf import settings
from django.http import Http404
from vehicles.models import Vehicle, Make, VehicleModel, Category
from vehicles.querysets import (
    published_vehicles, with_primary_image, with_all_images,
    with_documentation, with_features,
    apply_filters, apply_sorting, paginate,
    get_featured_vehicles, get_latest_arrivals,
    get_price_reduced_vehicles, get_related_vehicles,
    get_all_makes, get_all_categories, get_vehicle_stats,
    SORT_OPTIONS, SORT_LABELS,
)
from vehicles.cache import get_or_set, KEY_VEHICLE_DETAIL, TIMEOUT_MEDIUM
from currency.services import convert_price, get_supported_currencies

logger = logging.getLogger(__name__)


# ── Homepage ──────────────────────────────────────────────────────────────────

def homepage(request):
    try:
        featured_vehicles  = get_featured_vehicles(8)
        latest_arrivals    = get_latest_arrivals(8)
        price_reduced      = get_price_reduced_vehicles(6)
        all_makes          = get_all_makes()
        all_categories     = get_all_categories()
        stats              = get_vehicle_stats()
    except Exception as e:
        logger.error("Homepage data load error: %s", e)
        featured_vehicles = latest_arrivals = price_reduced = []
        all_makes = all_categories = []
        stats = {}

    context = {
        "featured_vehicles": featured_vehicles,
        "latest_arrivals":   latest_arrivals,
        "price_reduced":     price_reduced,
        "all_makes":         all_makes,
        "all_categories":    all_categories,
        "stats":             stats,
        "page_title":        f"{settings.DEALERSHIP_NAME} — Quality Vehicles in Kenya",
        "meta_description":  (
            f"Browse quality new and used vehicles at {settings.DEALERSHIP_NAME}. "
            "Find your perfect car, SUV, or pickup in Kenya."
        ),
    }
    return render(request, "catalogue/homepage.html", context)


# ── Vehicle Catalogue ─────────────────────────────────────────────────────────

def vehicle_list(request):
    """
    Main catalogue page with filtering, sorting, pagination.
    All filtering is DB-side — never loads all vehicles.
    """
    params   = request.GET
    sort_key = params.get("sort", "recommended")
    page_num = params.get("page", 1)

    try:
        page_num = int(page_num)
    except (ValueError, TypeError):
        page_num = 1

    # Build queryset
    qs = published_vehicles()
    qs = apply_filters(qs, params)
    qs = apply_sorting(qs, sort_key)
    qs = with_primary_image(qs)

    # Paginate
    page_obj, paginator = paginate(qs, page_num)

    # Filter sidebar data (cached)
    all_makes      = get_all_makes()
    all_categories = get_all_categories()

    # Build active filters summary for display
    active_filters = _build_active_filters(params)

    context = {
        "vehicles":       page_obj,
        "paginator":      paginator,
        "page_obj":       page_obj,
        "all_makes":      all_makes,
        "all_categories": all_categories,
        "sort_key":       sort_key,
        "sort_options":   SORT_LABELS,
        "active_filters": active_filters,
        "total_count":    paginator.count,
        "params":         params,
        "page_title":     "Browse Vehicles",
        "meta_description": (
            f"Search and filter {paginator.count:,} vehicles at "
            f"{settings.DEALERSHIP_NAME}. New, foreign used, and locally used cars in Kenya."
        ),
    }
    return render(request, "catalogue/vehicle_list.html", context)


# ── Vehicle Detail ────────────────────────────────────────────────────────────

def vehicle_detail(request, slug: str):
    """
    Vehicle detail page.
    Tracks view asynchronously — never blocks the page.
    """
    # Try cache first
    cache_key = KEY_VEHICLE_DETAIL.format(slug=slug)
    vehicle = None

    try:
        qs = (
            published_vehicles()
            .filter(slug=slug)
        )
        qs = with_all_images(qs)
        qs = with_documentation(qs)
        qs = with_features(qs)
        vehicle = qs.get()
    except Vehicle.DoesNotExist:
        raise Http404("Vehicle not found.")
    except Exception as e:
        logger.error("Vehicle detail error for slug %s: %s", slug, e)
        raise Http404("Vehicle not found.")

    # Related vehicles
    try:
        related = get_related_vehicles(vehicle)
    except Exception:
        related = []

    # Currency conversion
    currency     = getattr(request, "currency", "KES")
    converted    = None
    if vehicle.price and currency != "KES":
        converted = convert_price(vehicle.price, currency)

    # Async view tracking — never blocks response
    _track_vehicle_view(vehicle.pk, request)

    # WhatsApp URL
    whatsapp_msg = vehicle.get_whatsapp_message(settings.DEALERSHIP_SITE_URL)
    import urllib.parse
    whatsapp_url = (
        f"https://wa.me/{settings.WHATSAPP_BUSINESS_NUMBER}"
        f"?text={urllib.parse.quote(whatsapp_msg)}"
    )

    context = {
        "vehicle":           vehicle,
        "related_vehicles":  related,
        "whatsapp_url":      whatsapp_url,
        "converted_price":   converted,
        "current_currency":  currency,
        "page_title":        vehicle.get_seo_title(),
        "meta_description":  vehicle.get_seo_description(),
        "og_image":          vehicle.primary_image_url,
        "canonical_url":     request.build_absolute_uri(vehicle.get_absolute_url()),
    }
    return render(request, "catalogue/vehicle_detail.html", context)


# ── Browse by Make ────────────────────────────────────────────────────────────

def by_make(request, make_slug: str):
    make = get_object_or_404(Make, slug=make_slug)
    params = request.GET.copy()
    params["make"] = make_slug

    sort_key = request.GET.get("sort", "recommended")
    page_num = int(request.GET.get("page", 1))

    qs = with_primary_image(
        apply_sorting(
            apply_filters(published_vehicles(), params),
            sort_key,
        )
    )
    page_obj, paginator = paginate(qs, page_num)

    context = {
        "make":         make,
        "vehicles":     page_obj,
        "paginator":    paginator,
        "page_obj":     page_obj,
        "sort_key":     sort_key,
        "sort_options": SORT_LABELS,
        "total_count":  paginator.count,
        "page_title":   f"{make.name} Vehicles for Sale in Kenya | {settings.DEALERSHIP_NAME}",
        "meta_description": (
            f"Browse {paginator.count} {make.name} vehicles at {settings.DEALERSHIP_NAME}. "
            "New and used cars available in Kenya."
        ),
    }
    return render(request, "catalogue/by_make.html", context)


# ── Browse by Category ────────────────────────────────────────────────────────

def by_category(request, category_slug: str):
    category = get_object_or_404(Category, slug=category_slug)
    params   = request.GET.copy()
    params["category"] = category_slug

    sort_key = request.GET.get("sort", "recommended")
    page_num = int(request.GET.get("page", 1))

    qs = with_primary_image(
        apply_sorting(
            apply_filters(published_vehicles(), params),
            sort_key,
        )
    )
    page_obj, paginator = paginate(qs, page_num)

    context = {
        "category":    category,
        "vehicles":    page_obj,
        "paginator":   paginator,
        "page_obj":    page_obj,
        "sort_key":    sort_key,
        "sort_options": SORT_LABELS,
        "total_count": paginator.count,
        "page_title":  f"{category.name} for Sale in Kenya | {settings.DEALERSHIP_NAME}",
        "meta_description": (
            f"Browse {paginator.count} {category.name} vehicles at "
            f"{settings.DEALERSHIP_NAME}. Available in Kenya."
        ),
    }
    return render(request, "catalogue/by_category.html", context)


# ── Static pages ──────────────────────────────────────────────────────────────

def about(request):
    return render(request, "catalogue/about.html", {
        "page_title": f"About Us | {settings.DEALERSHIP_NAME}",
    })


def contact(request):
    whatsapp_url = f"https://wa.me/{settings.WHATSAPP_BUSINESS_NUMBER}"
    return render(request, "catalogue/contact.html", {
        "page_title":   f"Contact Us | {settings.DEALERSHIP_NAME}",
        "whatsapp_url": whatsapp_url,
    })



def privacy_policy(request):
    return render(request, "catalogue/privacy_policy.html", {
        "page_title": f"Privacy Policy | {settings.DEALERSHIP_NAME}",
    })


def terms(request):
    return render(request, "catalogue/terms.html", {
        "page_title": f"Terms & Conditions | {settings.DEALERSHIP_NAME}",
    })


# ── Error handlers ────────────────────────────────────────────────────────────

def handler404(request, exception=None):
    return render(request, "errors/404.html", status=404)


def handler500(request):
    return render(request, "errors/500.html", status=500)


def handler403(request, exception=None):
    return render(request, "errors/403.html", status=403)


def handler429(request, exception=None):
    return render(request, "errors/429.html", status=429)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_active_filters(params) -> list[dict]:
    """Build a list of active filters for the 'clear filter' UI chips."""
    active = []
    skip = {"page", "sort", "csrfmiddlewaretoken"}
    labels = {
        "q": "Search", "condition": "Condition", "make": "Make",
        "model": "Model", "category": "Category", "body_type": "Body Type",
        "fuel_type": "Fuel", "transmission": "Transmission",
        "price_min": "Min Price", "price_max": "Max Price",
        "year_min": "Min Year", "year_max": "Max Year",
        "featured": "Featured", "new_arrival": "New Arrival",
        "docs_ready": "Documents Ready", "inspected": "Inspected",
        "duty_paid": "Duty Paid", "transfer_ready": "Transfer Ready",
        "mileage_verified": "Mileage Verified",
    }
    for key, value in params.items():
        if key in skip or not value:
            continue
        label = labels.get(key, key.replace("_", " ").title())
        active.append({"key": key, "value": value, "label": f"{label}: {value}"})
    return active


def _track_vehicle_view(vehicle_id: int, request):
    """Queue view tracking asynchronously. Never blocks."""
    try:
        from django.core.cache import cache
        # Increment Redis counter — batch-flushed to DB by Celery
        counter_key = f"vehicle:views:{vehicle_id}"
        try:
            cache.incr(counter_key)
        except Exception:
            cache.set(counter_key, 1, timeout=86400)
    except Exception:
        pass
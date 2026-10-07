import logging
from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Q
from django.utils.decorators import method_decorator

logger = logging.getLogger(__name__)


@staff_member_required(login_url="/admin/login/")
def dashboard(request):
    """
    Main admin dashboard. Pulls live data from DB.
    Expensive aggregates should be cached (Phase 8 adds analytics models).
    """
    from vehicles.querysets import get_vehicle_stats
    from vehicles.models import Vehicle

    stats = get_vehicle_stats()

    # Recent vehicles
    try:
        recent_vehicles = (
            Vehicle.objects
            .select_related("make", "model")
            .order_by("-created_at")[:10]
        )
    except Exception:
        recent_vehicles = []

    # Top makes by inventory
    try:
        from vehicles.models import Make
        top_makes_qs = list(
            Make.objects.annotate(
                count=Count("vehicles", filter=Q(
                    vehicles__is_published=True,
                    vehicles__status="AVAILABLE",
                ))
            ).filter(count__gt=0).order_by("-count")[:6]
        )
        max_count = top_makes_qs[0].count if top_makes_qs else 1
        top_makes = [
            {"name": m.name, "count": m.count,
                "pct": int(m.count / max_count * 100)}
            for m in top_makes_qs
        ]
    except Exception:
        top_makes = []

    # Exchange rates
    try:
        from currency.models import ExchangeRate
        exchange_rates = ExchangeRate.objects.filter(
            base_currency="KES").order_by("target_currency")
        rate_updated_at = exchange_rates.first(
        ).fetched_at if exchange_rates.exists() else None
    except Exception:
        exchange_rates = []
        rate_updated_at = None

    context = {
        "stats":           stats,
        "recent_vehicles": recent_vehicles,
        "top_makes":       top_makes,
        "exchange_rates":  exchange_rates,
        "rate_updated_at": rate_updated_at,
        "active_section":  "dashboard",
        # Analytics placeholders — Phase 8 populates these
        "analytics_today": 0,
    }
    return render(request, "administration/dashboard.html", context)


@staff_member_required(login_url="/admin/login/")
def analytics(request):
    """Analytics view — Phase 8 full implementation."""
    from vehicles.querysets import get_vehicle_stats
    stats = get_vehicle_stats()
    context = {
        "stats":          stats,
        "active_section": "analytics",
        "page_heading":   "Analytics",
        "page_subheading": "Traffic and engagement data",
    }
    return render(request, "administration/analytics.html", context)

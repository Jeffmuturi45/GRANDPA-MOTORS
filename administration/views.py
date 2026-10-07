"""
Administration views — Phase 8 full analytics implementation.
Dashboard + Analytics page with real data from analytics models.
"""
import json
import logging
from datetime import timedelta

from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_GET

logger = logging.getLogger(__name__)


# ─── Dashboard ───────────────────────────────────────────────────────────────

@staff_member_required(login_url="/admin/login/")
def dashboard(request):
    """
    Main admin dashboard. Combines inventory stats + analytics overview.
    """
    from vehicles.querysets import get_vehicle_stats
    from vehicles.models import Vehicle, Make

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
            {"name": m.name, "count": m.count, "pct": int(m.count / max_count * 100)}
            for m in top_makes_qs
        ]
    except Exception:
        top_makes = []

    # Exchange rates
    try:
        from currency.models import ExchangeRate
        exchange_rates = ExchangeRate.objects.filter(
            base_currency="KES").order_by("target_currency")
        rate_updated_at = exchange_rates.first().fetched_at if exchange_rates.exists() else None
    except Exception:
        exchange_rates = []
        rate_updated_at = None

    # Analytics snapshot
    analytics = _get_analytics_snapshot()

    # Top viewed vehicles (last 7 days)
    try:
        top_vehicles = _get_top_vehicles(days=7, limit=5)
    except Exception:
        top_vehicles = []

    context = {
        "stats":            stats,
        "recent_vehicles":  recent_vehicles,
        "top_makes":        top_makes,
        "exchange_rates":   exchange_rates,
        "rate_updated_at":  rate_updated_at,
        "active_section":   "dashboard",
        "analytics":        analytics,
        "top_vehicles":     top_vehicles,
    }
    return render(request, "administration/dashboard.html", context)


# ─── Analytics page ──────────────────────────────────────────────────────────

@staff_member_required(login_url="/admin/login/")
def analytics(request):
    """Full analytics page with charts and detailed stats."""
    from vehicles.querysets import get_vehicle_stats

    stats    = get_vehicle_stats()
    snapshot = _get_analytics_snapshot()

    # 30-day chart data
    chart_data  = _get_chart_data(days=30)
    device_data = _get_device_breakdown()
    top_veh     = _get_top_vehicles(days=30, limit=10)
    top_pages   = _get_top_pages(days=30)

    context = {
        "stats":          stats,
        "active_section": "analytics",
        "page_heading":   "Analytics",
        "page_subheading": "Traffic and engagement data",
        "snapshot":       snapshot,
        "chart_labels":   json.dumps(chart_data["labels"]),
        "chart_views":    json.dumps(chart_data["views"]),
        "chart_sessions": json.dumps(chart_data["sessions"]),
        "device_data":    json.dumps(device_data),
        "top_vehicles":   top_veh,
        "top_pages":      top_pages,
    }
    return render(request, "administration/analytics.html", context)


# ─── AJAX / API endpoints ────────────────────────────────────────────────────

@staff_member_required(login_url="/admin/login/")
@require_GET
def analytics_chart_api(request):
    """AJAX endpoint for chart data. Supports ?days=7|30|90."""
    days = min(int(request.GET.get("days", 30)), 90)
    data = _get_chart_data(days=days)
    return JsonResponse(data)


@staff_member_required(login_url="/admin/login/")
@require_GET
def analytics_kpi_api(request):
    """AJAX endpoint returning live KPIs as JSON."""
    return JsonResponse(_get_analytics_snapshot())


# ─── Internal helpers ─────────────────────────────────────────────────────────

def _get_analytics_snapshot() -> dict:
    """Aggregated view/session stats for today / 7d / 30d / all-time."""
    try:
        from analytics.models import DailyStat
        now   = timezone.now().date()
        today = DailyStat.objects.filter(date=now).first()

        def _sum(qs, field):
            result = qs.aggregate(total=Sum(field))["total"]
            return result or 0

        week_qs  = DailyStat.objects.filter(date__gte=now - timedelta(days=7))
        month_qs = DailyStat.objects.filter(date__gte=now - timedelta(days=30))
        all_qs   = DailyStat.objects.all()

        prev_week_qs  = DailyStat.objects.filter(
            date__gte=now - timedelta(days=14),
            date__lt=now - timedelta(days=7),
        )
        prev_month_qs = DailyStat.objects.filter(
            date__gte=now - timedelta(days=60),
            date__lt=now - timedelta(days=30),
        )

        this_week  = _sum(week_qs,  "total_views")
        prev_week  = _sum(prev_week_qs, "total_views")
        this_month = _sum(month_qs, "total_views")
        prev_month = _sum(prev_month_qs, "total_views")

        def pct_change(current, previous):
            if not previous:
                return None
            return round((current - previous) / previous * 100, 1)

        return {
            "today":          today.total_views if today else 0,
            "today_sessions": today.unique_sessions if today else 0,
            "week":           this_week,
            "week_change":    pct_change(this_week, prev_week),
            "month":          this_month,
            "month_change":   pct_change(this_month, prev_month),
            "all_time":       _sum(all_qs, "total_views"),
            "all_sessions":   _sum(all_qs, "unique_sessions"),
        }
    except Exception as e:
        logger.warning("_get_analytics_snapshot failed: %s", e)
        return {
            "today": 0, "today_sessions": 0,
            "week": 0, "week_change": None,
            "month": 0, "month_change": None,
            "all_time": 0, "all_sessions": 0,
        }


def _get_chart_data(days: int = 30) -> dict:
    """Return labels + views + sessions arrays for Chart.js."""
    try:
        from analytics.models import DailyStat
        now     = timezone.now().date()
        start   = now - timedelta(days=days - 1)
        qs      = DailyStat.objects.filter(date__gte=start, date__lte=now).order_by("date")
        stat_map = {s.date: s for s in qs}

        labels, views, sessions = [], [], []
        for i in range(days):
            day = start + timedelta(days=i)
            s   = stat_map.get(day)
            labels.append(day.strftime("%d %b"))
            views.append(s.total_views if s else 0)
            sessions.append(s.unique_sessions if s else 0)

        return {"labels": labels, "views": views, "sessions": sessions}
    except Exception as e:
        logger.warning("_get_chart_data failed: %s", e)
        return {"labels": [], "views": [], "sessions": []}


def _get_device_breakdown() -> dict:
    """Aggregate last-30-days device breakdown for doughnut chart."""
    try:
        from analytics.models import DailyStat
        from django.db.models import Sum
        now   = timezone.now().date()
        agg   = DailyStat.objects.filter(
            date__gte=now - timedelta(days=30)
        ).aggregate(
            mobile=Sum("mobile_views"),
            desktop=Sum("desktop_views"),
            tablet=Sum("tablet_views"),
        )
        return {
            "mobile":  agg["mobile"]  or 0,
            "desktop": agg["desktop"] or 0,
            "tablet":  agg["tablet"]  or 0,
        }
    except Exception:
        return {"mobile": 0, "desktop": 0, "tablet": 0}


def _get_top_vehicles(days: int = 7, limit: int = 5) -> list:
    """Top vehicles by views in the last N days."""
    try:
        from analytics.models import TopVehicleStat
        from django.db.models import Sum
        now   = timezone.now().date()
        start = now - timedelta(days=days)
        qs = (
            TopVehicleStat.objects
            .filter(date__gte=start)
            .select_related("vehicle__make", "vehicle__model")
            .values("vehicle__id", "vehicle__slug",
                    "vehicle__make__name", "vehicle__model__name",
                    "vehicle__year", "vehicle__price", "vehicle__status")
            .annotate(total_views=Sum("view_count"), total_inquiries=Sum("inquiry_count"))
            .order_by("-total_views")[:limit]
        )
        return list(qs)
    except Exception as e:
        logger.warning("_get_top_vehicles failed: %s", e)
        return []


def _get_top_pages(days: int = 30) -> list:
    """Top pages from DailyStat.top_paths aggregation."""
    try:
        from analytics.models import DailyStat
        now   = timezone.now().date()
        qs    = DailyStat.objects.filter(date__gte=now - timedelta(days=days))
        # Aggregate counts across days
        page_counts: dict = {}
        for stat in qs:
            for entry in stat.top_paths or []:
                p = entry.get("path", "")
                page_counts[p] = page_counts.get(p, 0) + entry.get("count", 0)
        return sorted(
            [{"path": k, "count": v} for k, v in page_counts.items()],
            key=lambda x: x["count"], reverse=True
        )[:10]
    except Exception:
        return []

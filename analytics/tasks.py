"""
Analytics Celery tasks - Phase 8 full implementation.
All DB writes are async; middleware just queues, never blocks.
"""
import logging
from celery import shared_task
from django.utils import timezone
from django.db.models import Count

logger = logging.getLogger(__name__)


@shared_task(
    name="analytics.tasks.track_page_view",
    ignore_result=True,
    queue="analytics",
)
def track_page_view(
    path: str,
    method: str,
    status_code: int,
    user_agent: str,
    referer: str,
    ip_hash: str,
    session_key: str,
):
    """
    Async page view tracking.
    Parses UA, writes PageView row, and increments vehicle view if applicable.
    """
    try:
        from analytics.models import PageView, VehicleView
        # Parse user agent
        device_type, browser, os_name, is_bot = _parse_ua(user_agent)

        if is_bot:
            return  # Don't track bots

        pv = PageView.objects.create(
            path=path,
            method=method,
            status_code=status_code,
            ip_hash=ip_hash,
            session_key=session_key,
            user_agent=user_agent[:500],
            referer=referer[:500],
            device_type=device_type,
            browser=browser,
            os=os_name,
            is_bot=is_bot,
        )

        # If vehicle detail page, also log VehicleView
        import re
        m = re.match(r"^/vehicles/([a-z0-9-]+)/$", path)
        if not m:
            m = re.match(r"^/([a-z0-9-]+)/$", path)
        if m:
            slug = m.group(1)
            try:
                from vehicles.models import Vehicle
                vehicle = Vehicle.objects.filter(slug=slug).first()
                if vehicle:
                    VehicleView.objects.create(
                        vehicle=vehicle,
                        session_key=session_key,
                        ip_hash=ip_hash,
                        device_type=device_type,
                        referer=referer[:500],
                    )
            except Exception as e:
                logger.debug("VehicleView create failed: %s", e)

    except Exception as e:
        logger.error("track_page_view failed: %s", e)


@shared_task(name="analytics.tasks.aggregate_daily_stats")
def aggregate_daily_stats():
    """
    Pre-aggregate yesterday's analytics into DailyStat.
    Called by Celery Beat daily at midnight.
    """
    try:
        from analytics.models import PageView, DailyStat, VehicleView, TopVehicleStat
        yesterday = (timezone.now() - timezone.timedelta(days=1)).date()

        qs = PageView.objects.filter(
            created_at__date=yesterday,
            is_bot=False,
        )
        total_views     = qs.count()
        unique_sessions = qs.exclude(session_key="").values("session_key").distinct().count()
        vehicle_views   = VehicleView.objects.filter(created_at__date=yesterday).count()
        mobile_views    = qs.filter(device_type="mobile").count()
        desktop_views   = qs.filter(device_type="desktop").count()
        tablet_views    = qs.filter(device_type="tablet").count()

        top_paths = list(
            qs.values("path").annotate(count=Count("id"))
            .order_by("-count")[:10]
            .values("path", "count")
        )
        top_referers = list(
            qs.exclude(referer="").values("referer")
            .annotate(count=Count("id"))
            .order_by("-count")[:10]
            .values("referer", "count")
        )

        DailyStat.objects.update_or_create(
            date=yesterday,
            defaults=dict(
                total_views=total_views,
                unique_sessions=unique_sessions,
                vehicle_page_views=vehicle_views,
                mobile_views=mobile_views,
                desktop_views=desktop_views,
                tablet_views=tablet_views,
                top_paths=top_paths,
                top_referers=top_referers,
            ),
        )

        # Top vehicles
        top_vehicles = (
            VehicleView.objects
            .filter(created_at__date=yesterday)
            .values("vehicle_id")
            .annotate(view_count=Count("id"))
            .order_by("-view_count")[:20]
        )
        for rank, entry in enumerate(top_vehicles, 1):
            TopVehicleStat.objects.update_or_create(
                date=yesterday,
                vehicle_id=entry["vehicle_id"],
                defaults=dict(view_count=entry["view_count"], rank=rank),
            )

        logger.info("Daily stats aggregated for %s: %d views", yesterday, total_views)

    except Exception as e:
        logger.error("aggregate_daily_stats failed: %s", e)


# ── UA Parsing helper ────────────────────────────────────────────────

def _parse_ua(ua_string: str):
    """Return (device_type, browser, os, is_bot) tuple."""
    ua_lower = ua_string.lower()
    # Bot detection
    bot_signals = ["bot", "crawl", "spider", "slurp", "mediapartner", "facebookexternalhit",
                   "curl", "wget", "python-requests", "go-http", "java/", "okhttp"]
    is_bot = any(sig in ua_lower for sig in bot_signals)
    # Device type
    if any(x in ua_lower for x in ["mobile", "android", "iphone", "blackberry", "windows phone"]):
        device_type = "mobile"
    elif any(x in ua_lower for x in ["ipad", "tablet", "kindle"]):
        device_type = "tablet"
    else:
        device_type = "desktop"
    # Browser
    if "edg" in ua_lower:
        browser = "Edge"
    elif "chrome" in ua_lower:
        browser = "Chrome"
    elif "firefox" in ua_lower:
        browser = "Firefox"
    elif "safari" in ua_lower:
        browser = "Safari"
    elif "opera" in ua_lower or "opr" in ua_lower:
        browser = "Opera"
    else:
        browser = "Other"
    # OS
    if "windows" in ua_lower:
        os_name = "Windows"
    elif "mac os" in ua_lower or "macos" in ua_lower:
        os_name = "macOS"
    elif "android" in ua_lower:
        os_name = "Android"
    elif "iphone" in ua_lower or "ipad" in ua_lower:
        os_name = "iOS"
    elif "linux" in ua_lower:
        os_name = "Linux"
    else:
        os_name = "Other"

    return device_type, browser, os_name, is_bot

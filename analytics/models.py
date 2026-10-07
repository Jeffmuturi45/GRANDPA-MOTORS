"""
Analytics models - Phase 8 implementation.
Tracks page views, vehicle views, and daily aggregates.
All writes happen asynchronously via Celery - never blocks requests.
"""
import hashlib
from django.db import models
from django.utils import timezone


class PageView(models.Model):
    """
    Raw page view event. Written by Celery task, never synchronously.
    Rows are pruned after 90 days; aggregates live in DailyStat.
    """
    path        = models.CharField(max_length=500, db_index=True)
    method      = models.CharField(max_length=10, default="GET")
    status_code = models.PositiveSmallIntegerField(default=200)
    ip_hash     = models.CharField(max_length=64, blank=True)      # SHA-256 prefix, not raw IP
    session_key = models.CharField(max_length=40, blank=True, db_index=True)
    user_agent  = models.CharField(max_length=500, blank=True)
    referer     = models.CharField(max_length=500, blank=True)
    # Parsed UA fields (populated by Celery task)
    device_type = models.CharField(max_length=20, blank=True)      # mobile / tablet / desktop
    browser     = models.CharField(max_length=50, blank=True)
    os          = models.CharField(max_length=50, blank=True)
    is_bot      = models.BooleanField(default=False, db_index=True)
    created_at  = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes  = [
            models.Index(fields=["path", "created_at"]),
            models.Index(fields=["created_at", "is_bot"]),
            models.Index(fields=["session_key"]),
        ]
        verbose_name        = "Page View"
        verbose_name_plural = "Page Views"

    def __str__(self):
        return f"{self.path} — {self.created_at:%Y-%m-%d %H:%M}"


class VehicleView(models.Model):
    """
    Tracks views on individual vehicle detail pages.
    Linked to PageView for joined analysis.
    """
    vehicle    = models.ForeignKey(
        "vehicles.Vehicle", on_delete=models.CASCADE,
        related_name="analytics_views"
    )
    session_key = models.CharField(max_length=40, blank=True, db_index=True)
    ip_hash     = models.CharField(max_length=64, blank=True)
    device_type = models.CharField(max_length=20, blank=True)
    referer     = models.CharField(max_length=500, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=["vehicle", "created_at"]),
            models.Index(fields=["created_at"]),
        ]
        verbose_name        = "Vehicle View"
        verbose_name_plural = "Vehicle Views"

    def __str__(self):
        return f"{self.vehicle} — {self.created_at:%Y-%m-%d}"


class DailyStat(models.Model):
    """
    Pre-aggregated daily analytics. Populated by Celery Beat nightly.
    This is what the dashboard queries - never the raw PageView table.
    """
    date              = models.DateField(unique=True, db_index=True)
    # Traffic
    total_views       = models.PositiveIntegerField(default=0)
    unique_sessions   = models.PositiveIntegerField(default=0)
    vehicle_page_views = models.PositiveIntegerField(default=0)
    # Device breakdown
    mobile_views      = models.PositiveIntegerField(default=0)
    desktop_views     = models.PositiveIntegerField(default=0)
    tablet_views      = models.PositiveIntegerField(default=0)
    # Top paths (JSON list of {path, count})
    top_paths         = models.JSONField(default=list, blank=True)
    # Referrers (JSON list of {referer, count})
    top_referers      = models.JSONField(default=list, blank=True)
    created_at        = models.DateTimeField(auto_now_add=True)
    updated_at        = models.DateTimeField(auto_now=True)

    class Meta:
        ordering            = ["-date"]
        verbose_name        = "Daily Stat"
        verbose_name_plural = "Daily Stats"

    def __str__(self):
        return f"{self.date} — {self.total_views} views"


class TopVehicleStat(models.Model):
    """
    Daily top-performing vehicles by views and inquiries.
    Written by aggregate_daily_stats Celery task.
    """
    date         = models.DateField(db_index=True)
    vehicle      = models.ForeignKey(
        "vehicles.Vehicle", on_delete=models.CASCADE,
        related_name="daily_stats"
    )
    view_count   = models.PositiveIntegerField(default=0)
    inquiry_count = models.PositiveIntegerField(default=0)
    rank         = models.PositiveSmallIntegerField(default=0)  # 1 = most viewed

    class Meta:
        unique_together     = [("date", "vehicle")]
        ordering            = ["date", "rank"]
        verbose_name        = "Top Vehicle Stat"
        verbose_name_plural = "Top Vehicle Stats"

    def __str__(self):
        return f"{self.date} #{self.rank} — {self.vehicle}"

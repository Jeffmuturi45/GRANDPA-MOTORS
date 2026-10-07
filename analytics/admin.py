from django.contrib import admin
from .models import PageView, VehicleView, DailyStat, TopVehicleStat


@admin.register(PageView)
class PageViewAdmin(admin.ModelAdmin):
    list_display  = ["path", "device_type", "browser", "status_code", "is_bot", "created_at"]
    list_filter   = ["is_bot", "device_type", "status_code"]
    search_fields = ["path", "ip_hash", "session_key"]
    readonly_fields = [f.name for f in PageView._meta.fields]
    date_hierarchy = "created_at"


@admin.register(DailyStat)
class DailyStatAdmin(admin.ModelAdmin):
    list_display  = ["date", "total_views", "unique_sessions", "vehicle_page_views",
                     "mobile_views", "desktop_views"]
    date_hierarchy = "date"
    readonly_fields = ["created_at", "updated_at"]


@admin.register(TopVehicleStat)
class TopVehicleStatAdmin(admin.ModelAdmin):
    list_display  = ["date", "rank", "vehicle", "view_count", "inquiry_count"]
    list_filter   = ["date"]
    date_hierarchy = "date"

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import (
    Make, VehicleModel, Category, Feature,
    Vehicle, VehicleImage, VehicleDocumentation,
    VehicleVerification, PriceHistory, AuditLog,
)


@admin.register(Make)
class MakeAdmin(admin.ModelAdmin):
    list_display  = ["name", "is_popular", "sort_order", "vehicle_count"]
    list_editable = ["is_popular", "sort_order"]
    search_fields = ["name"]
    prepopulated_fields = {"slug": ("name",)}

    def vehicle_count(self, obj):
        return obj.vehicles.filter(is_published=True).count()
    vehicle_count.short_description = "Published Vehicles"


@admin.register(VehicleModel)
class VehicleModelAdmin(admin.ModelAdmin):
    list_display  = ["name", "make", "vehicle_count"]
    list_filter   = ["make"]
    search_fields = ["name", "make__name"]
    prepopulated_fields = {"slug": ("name",)}

    def vehicle_count(self, obj):
        return obj.vehicles.filter(is_published=True).count()
    vehicle_count.short_description = "Published Vehicles"


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display  = ["name", "is_popular", "sort_order", "vehicle_count"]
    list_editable = ["is_popular", "sort_order"]
    prepopulated_fields = {"slug": ("name",)}

    def vehicle_count(self, obj):
        return obj.vehicles.filter(is_published=True).count()
    vehicle_count.short_description = "Published Vehicles"


@admin.register(Feature)
class FeatureAdmin(admin.ModelAdmin):
    list_display  = ["name", "category", "sort_order"]
    list_editable = ["sort_order"]
    list_filter   = ["category"]
    search_fields = ["name"]
    prepopulated_fields = {"slug": ("name",)}


# ── Inlines ──────────────────────────────────

class VehicleImageInline(admin.TabularInline):
    model      = VehicleImage
    extra      = 3
    fields     = ["image", "image_preview", "is_primary", "sort_order", "alt_text", "caption"]
    readonly_fields = ["image_preview"]
    ordering   = ["sort_order"]

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="height:60px;border-radius:4px;" />',
                obj.image.url
            )
        return "—"
    image_preview.short_description = "Preview"


class VehicleDocumentationInline(admin.StackedInline):
    model  = VehicleDocumentation
    extra  = 0
    fields = [
        ("logbook_status", "import_docs"),
        ("duty_status", "transfer_status"),
        "notes",
    ]


class VehicleVerificationInline(admin.StackedInline):
    model  = VehicleVerification
    extra  = 0
    fields = [
        ("inspection_status", "inspection_date"),
        ("mileage_verified", "document_verified"),
        "inspection_notes",
    ]


class PriceHistoryInline(admin.TabularInline):
    model      = PriceHistory
    extra      = 0
    readonly_fields = ["old_price", "new_price", "changed_by", "changed_at", "note"]
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


# ── Main Vehicle Admin ────────────────────────

@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = [
        "stock_number", "thumbnail_preview", "title", "year",
        "condition_badge", "status_badge", "price_display",
        "featured", "new_arrival", "is_published", "created_at",
    ]
    list_display_links = ["stock_number", "title"]
    list_filter = [
        "status", "condition", "is_published", "featured",
        "new_arrival", "make", "category", "fuel_type",
        "transmission", "year",
    ]
    search_fields = [
        "stock_number", "make__name", "model__name",
        "variant", "slug", "exterior_color",
    ]
    list_editable = ["featured", "new_arrival", "is_published"]
    readonly_fields = [
        "uuid", "stock_number", "slug", "view_count",
        "inquiry_count", "published_at", "created_at", "updated_at",
        "whatsapp_link_preview",
    ]
    filter_horizontal = ["features"]
    save_on_top = True
    inlines = [
        VehicleImageInline,
        VehicleDocumentationInline,
        VehicleVerificationInline,
        PriceHistoryInline,
    ]

    fieldsets = (
        ("Identity", {
            "fields": (("uuid", "stock_number"), "slug"),
        }),
        ("Classification", {
            "fields": (
                ("make", "model", "variant"),
                ("year", "condition"),
                ("category", "body_type"),
            ),
        }),
        ("Pricing", {
            "fields": (
                ("price", "previous_price", "pricing_type", "currency"),
            ),
        }),
        ("Specifications", {
            "fields": (
                ("mileage", "fuel_type"),
                ("transmission", "drivetrain"),
                ("engine_capacity", "engine_power"),
                ("exterior_color", "interior_color"),
                "location",
            ),
        }),
        ("Features", {
            "fields": ("features",),
            "classes": ("collapse",),
        }),
        ("Description", {
            "fields": ("description",),
        }),
        ("Publishing & Flags", {
            "fields": (
                ("status", "is_published"),
                ("featured", "new_arrival"),
                ("published_at", "created_at", "updated_at"),
            ),
        }),
        ("Analytics", {
            "fields": (("view_count", "inquiry_count"),),
            "classes": ("collapse",),
        }),
        ("SEO", {
            "fields": ("seo_title", "seo_description"),
            "classes": ("collapse",),
        }),
        ("WhatsApp Preview", {
            "fields": ("whatsapp_link_preview",),
            "classes": ("collapse",),
        }),
    )

    # ── Custom display methods ─────────────────

    def thumbnail_preview(self, obj):
        img = obj.primary_image
        if img:
            return format_html(
                '<img src="{}" style="height:48px;width:72px;object-fit:cover;border-radius:4px;" />',
                img.image.url
            )
        return format_html('<span style="color:#999;">No image</span>')
    thumbnail_preview.short_description = ""

    def title(self, obj):
        return obj.title
    title.short_description = "Vehicle"

    def condition_badge(self, obj):
        colors = {
            "NEW": "#10b981", "FOREIGN_USED": "#3b82f6",
            "LOCALLY_USED": "#f59e0b", "RECONDITIONED": "#8b5cf6",
        }
        color = colors.get(obj.condition, "#6b7280")
        return format_html(
            '<span style="background:{};color:white;padding:2px 8px;border-radius:12px;font-size:11px;">{}</span>',
            color, obj.get_condition_display()
        )
    condition_badge.short_description = "Condition"

    def status_badge(self, obj):
        colors = {
            "AVAILABLE": "#10b981", "RESERVED": "#f59e0b",
            "SOLD": "#ef4444", "ARCHIVED": "#6b7280",
        }
        color = colors.get(obj.status, "#6b7280")
        return format_html(
            '<span style="background:{};color:white;padding:2px 8px;border-radius:12px;font-size:11px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = "Status"

    def price_display(self, obj):
        return obj.display_price
    price_display.short_description = "Price"

    def whatsapp_link_preview(self, obj):
        from django.conf import settings
        if not obj.pk:
            return "Save the vehicle first to preview WhatsApp link."
        msg = obj.get_whatsapp_message(settings.DEALERSHIP_SITE_URL)
        import urllib.parse
        encoded = urllib.parse.quote(msg)
        number = settings.WHATSAPP_BUSINESS_NUMBER
        url = f"https://wa.me/{number}?text={encoded}"
        return format_html(
            '<a href="{}" target="_blank" style="color:#25d366;font-weight:bold;">Preview WhatsApp Link ↗</a>',
            url
        )
    whatsapp_link_preview.short_description = "WhatsApp Link"

    # ── Bulk actions ──────────────────────────

    actions = [
        "action_publish", "action_unpublish",
        "action_mark_featured", "action_unmark_featured",
        "action_mark_sold", "action_mark_reserved",
        "action_mark_available", "action_archive",
    ]

    @admin.action(description="✓ Publish selected vehicles")
    def action_publish(self, request, queryset):
        updated = queryset.filter(is_published=False).update(
            is_published=True, published_at=timezone.now()
        )
        self.message_user(request, f"{updated} vehicle(s) published.")

    @admin.action(description="✗ Unpublish selected vehicles")
    def action_unpublish(self, request, queryset):
        updated = queryset.update(is_published=False, published_at=None)
        self.message_user(request, f"{updated} vehicle(s) unpublished.")

    @admin.action(description="⭐ Mark as Featured")
    def action_mark_featured(self, request, queryset):
        updated = queryset.update(featured=True)
        self.message_user(request, f"{updated} vehicle(s) marked as featured.")

    @admin.action(description="Remove from Featured")
    def action_unmark_featured(self, request, queryset):
        updated = queryset.update(featured=False)
        self.message_user(request, f"{updated} vehicle(s) removed from featured.")

    @admin.action(description="Mark as Sold")
    def action_mark_sold(self, request, queryset):
        updated = queryset.update(status="SOLD")
        self.message_user(request, f"{updated} vehicle(s) marked as sold.")

    @admin.action(description="Mark as Reserved")
    def action_mark_reserved(self, request, queryset):
        updated = queryset.update(status="RESERVED")
        self.message_user(request, f"{updated} vehicle(s) marked as reserved.")

    @admin.action(description="Mark as Available")
    def action_mark_available(self, request, queryset):
        updated = queryset.update(status="AVAILABLE")
        self.message_user(request, f"{updated} vehicle(s) marked as available.")

    @admin.action(description="Archive selected vehicles")
    def action_archive(self, request, queryset):
        updated = queryset.update(status="ARCHIVED", is_published=False)
        self.message_user(request, f"{updated} vehicle(s) archived.")


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display  = ["created_at", "action", "vehicle", "user", "detail"]
    list_filter   = ["action", "created_at"]
    search_fields = ["vehicle__stock_number", "detail"]
    readonly_fields = ["vehicle", "action", "user", "detail", "created_at"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
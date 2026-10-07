from django.contrib import admin
from .models import ExchangeRate, CurrencyConfig


@admin.register(ExchangeRate)
class ExchangeRateAdmin(admin.ModelAdmin):
    list_display = ["base_currency", "target_currency",
                    "rate", "fetched_at", "is_fallback", "is_stale"]
    list_filter = ["base_currency", "is_fallback"]
    readonly_fields = ["fetched_at", "is_fallback"]

    def is_stale(self, obj):
        return obj.is_stale
    is_stale.boolean = True
    is_stale.short_description = "Stale?"

    def has_add_permission(self, request):
        return False  # Rates are managed by Celery only


@admin.register(CurrencyConfig)
class CurrencyConfigAdmin(admin.ModelAdmin):
    list_display = ["country_code", "country_name",
                    "currency_code", "currency_symbol"]
    search_fields = ["country_code", "country_name", "currency_code"]

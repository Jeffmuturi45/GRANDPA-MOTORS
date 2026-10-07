from django.db import models
from django.utils import timezone


class ExchangeRate(models.Model):
    """
    Cached exchange rates. KES is always the base currency.
    Rates are refreshed hourly by Celery — never fetched per-request.
    """
    base_currency = models.CharField(max_length=3, default="KES")
    target_currency = models.CharField(max_length=3, db_index=True)
    rate = models.DecimalField(max_digits=20, decimal_places=8)
    fetched_at = models.DateTimeField(default=timezone.now)
    is_fallback = models.BooleanField(
        default=False,
        help_text="True if the API was unavailable and this is a cached fallback"
    )

    class Meta:
        unique_together = [("base_currency", "target_currency")]
        verbose_name = "Exchange Rate"
        verbose_name_plural = "Exchange Rates"
        indexes = [
            models.Index(fields=["target_currency", "fetched_at"]),
        ]

    def __str__(self):
        return f"{self.base_currency}/{self.target_currency} = {self.rate}"

    @property
    def is_stale(self) -> bool:
        """Rate is stale if older than 2 hours."""
        age = timezone.now() - self.fetched_at
        return age.total_seconds() > 7200


class CurrencyConfig(models.Model):
    """
    Maps countries to their preferred display currency.
    Used for IP-based currency detection.
    """
    country_code = models.CharField(max_length=2, unique=True, db_index=True)
    country_name = models.CharField(max_length=100)
    currency_code = models.CharField(max_length=3)
    currency_symbol = models.CharField(max_length=10)

    class Meta:
        verbose_name = "Currency Config"
        verbose_name_plural = "Currency Configs"
        ordering = ["country_name"]

    def __str__(self):
        return f"{self.country_code} → {self.currency_code}"

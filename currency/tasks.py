import logging
import requests
from decimal import Decimal
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from celery import shared_task

logger = logging.getLogger(__name__)

SUPPORTED_TARGETS = ["USD", "GBP", "EUR", "UGX", "TZS", "AED"]
CACHE_KEY_RATE = "currency:rate:KES:{target}"
CACHE_KEY_ALL = "currency:all_rates"


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=300,
    name="currency.tasks.refresh_exchange_rates",
)
def refresh_exchange_rates(self):
    """
    Fetch fresh exchange rates from the configured API.
    Stores results in both PostgreSQL and Redis.
    Runs hourly via Celery Beat.
    Never blocks user requests — purely background.
    """
    api_key = settings.EXCHANGE_RATE_API_KEY
    api_url = settings.EXCHANGE_RATE_API_URL

    if not api_key:
        logger.warning(
            "EXCHANGE_RATE_API_KEY not configured — skipping rate refresh.")
        return

    try:
        url = f"{api_url}/{api_key}/latest/KES"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data.get("result") != "success":
            raise ValueError(f"API returned non-success: {data.get('result')}")

        rates = data.get("conversion_rates", {})
        updated = []

        from .models import ExchangeRate

        for target in SUPPORTED_TARGETS:
            if target not in rates:
                logger.warning("Rate for %s not in API response", target)
                continue

            rate_value = Decimal(str(rates[target]))

            ExchangeRate.objects.update_or_create(
                base_currency="KES",
                target_currency=target,
                defaults={
                    "rate":        rate_value,
                    "fetched_at":  timezone.now(),
                    "is_fallback": False,
                },
            )

            # Warm Redis cache immediately
            cache.set(
                CACHE_KEY_RATE.format(target=target),
                str(rate_value),
                timeout=3600,
            )
            updated.append(target)

        # Invalidate the all-rates summary cache
        cache.delete(CACHE_KEY_ALL)

        logger.info("Exchange rates refreshed: %s", ", ".join(updated))
        return {"updated": updated, "timestamp": timezone.now().isoformat()}

    except requests.RequestException as exc:
        logger.error("Exchange rate API request failed: %s", exc)
        # Retry up to 3 times with exponential backoff
        raise self.retry(exc=exc, countdown=2 ** self.request.retries * 60)
    except Exception as exc:
        logger.error("Exchange rate refresh failed: %s", exc)
        raise

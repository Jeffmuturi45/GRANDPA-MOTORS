import logging
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional
from django.conf import settings
from django.core.cache import cache
from .models import ExchangeRate

logger = logging.getLogger(__name__)

# ── Currency metadata ─────────────────────────────────────────────────────────

CURRENCY_META = {
    "KES": {"symbol": "KSh",  "name": "Kenyan Shilling",    "decimals": 0},
    "USD": {"symbol": "$",    "name": "US Dollar",           "decimals": 2},
    "GBP": {"symbol": "£",    "name": "British Pound",       "decimals": 2},
    "EUR": {"symbol": "€",    "name": "Euro",                "decimals": 2},
    "UGX": {"symbol": "USh",  "name": "Ugandan Shilling",   "decimals": 0},
    "TZS": {"symbol": "TSh",  "name": "Tanzanian Shilling", "decimals": 0},
    "AED": {"symbol": "AED",  "name": "UAE Dirham",          "decimals": 2},
}

# Hardcoded emergency fallback rates (last-resort only — never primary)
FALLBACK_RATES_FROM_KES = {
    "USD": Decimal("0.00775"),
    "GBP": Decimal("0.00615"),
    "EUR": Decimal("0.00715"),
    "UGX": Decimal("28.50"),
    "TZS": Decimal("20.50"),
    "AED": Decimal("0.02845"),
}

CACHE_KEY_RATE = "currency:rate:{base}:{target}"
CACHE_KEY_ALL = "currency:all_rates"
CACHE_TIMEOUT = 3600  # 1 hour


# ── Public API ────────────────────────────────────────────────────────────────

def get_rate(target: str, base: str = "KES") -> Optional[Decimal]:
    """
    Get exchange rate for target currency from base (default KES).
    Order of precedence:
      1. Redis cache
      2. Database
      3. Hardcoded fallback
    Never blocks — always returns something or None.
    """
    if base == target:
        return Decimal("1")

    # 1. Redis cache
    cache_key = CACHE_KEY_RATE.format(base=base, target=target)
    cached = cache.get(cache_key)
    if cached is not None:
        return Decimal(str(cached))

    # 2. Database
    try:
        rate_obj = ExchangeRate.objects.get(
            base_currency=base, target_currency=target
        )
        rate = rate_obj.rate
        # Warm cache
        cache.set(cache_key, str(rate), timeout=CACHE_TIMEOUT)
        return rate
    except ExchangeRate.DoesNotExist:
        pass
    except Exception as e:
        logger.warning("DB rate lookup failed for %s/%s: %s", base, target, e)

    # 3. Hardcoded fallback
    if base == "KES" and target in FALLBACK_RATES_FROM_KES:
        logger.warning("Using hardcoded fallback rate for %s", target)
        return FALLBACK_RATES_FROM_KES[target]

    return None


def convert_price(
    amount_kes: Decimal,
    target_currency: str,
) -> Optional[dict]:
    """
    Convert a KES price to target currency.
    Returns dict with converted amount, symbol, and metadata.
    Returns None if conversion is not possible.
    Never raises — always safe to call.
    """
    if not amount_kes or target_currency == "KES":
        meta = CURRENCY_META.get("KES", {})
        return {
            "amount":      amount_kes,
            "currency":    "KES",
            "symbol":      meta.get("symbol", "KSh"),
            "name":        meta.get("name", "Kenyan Shilling"),
            "is_converted": False,
            "is_fallback":  False,
            "formatted":   _format_amount(amount_kes, "KES"),
        }

    try:
        rate = get_rate(target=target_currency, base="KES")
        if rate is None:
            return None

        converted = (amount_kes * rate).quantize(
            Decimal("1") if CURRENCY_META.get(target_currency, {}).get("decimals", 2) == 0
            else Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )

        meta = CURRENCY_META.get(
            target_currency, {"symbol": target_currency, "name": target_currency})

        # Check if using fallback
        is_fallback = target_currency in FALLBACK_RATES_FROM_KES and _is_using_fallback(
            target_currency)

        return {
            "amount":       converted,
            "currency":     target_currency,
            "symbol":       meta.get("symbol", target_currency),
            "name":         meta.get("name", target_currency),
            "is_converted": True,
            "is_fallback":  is_fallback,
            "formatted":    _format_amount(converted, target_currency),
        }
    except Exception as e:
        logger.error("Price conversion error KES→%s: %s", target_currency, e)
        return None


def get_all_rates() -> dict:
    """Return all cached rates for the currency switcher UI."""
    cached = cache.get(CACHE_KEY_ALL)
    if cached:
        return cached

    try:
        rates = {
            r.target_currency: str(r.rate)
            for r in ExchangeRate.objects.filter(base_currency="KES")
        }
        cache.set(CACHE_KEY_ALL, rates, timeout=CACHE_TIMEOUT)
        return rates
    except Exception:
        return {}


def get_supported_currencies() -> list[dict]:
    """Return list of supported currencies for the selector UI."""
    return [
        {
            "code":   code,
            "symbol": meta["symbol"],
            "name":   meta["name"],
        }
        for code, meta in CURRENCY_META.items()
    ]


def get_currency_symbol(code: str) -> str:
    return CURRENCY_META.get(code, {}).get("symbol", code)


# ── Internal helpers ──────────────────────────────────────────────────────────

def _format_amount(amount: Decimal, currency: str) -> str:
    meta = CURRENCY_META.get(currency, {"symbol": currency, "decimals": 2})
    symbol = meta["symbol"]
    decimals = meta["decimals"]
    if decimals == 0:
        return f"{symbol} {amount:,.0f}"
    return f"{symbol} {amount:,.{decimals}f}"


def _is_using_fallback(currency: str) -> bool:
    """Check if the live DB rate exists for this currency."""
    try:
        ExchangeRate.objects.get(base_currency="KES", target_currency=currency)
        return False
    except ExchangeRate.DoesNotExist:
        return True

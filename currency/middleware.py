import logging
import requests
from django.conf import settings
from django.core.cache import cache
from .services import CURRENCY_META, get_currency_symbol

logger = logging.getLogger(__name__)

SUPPORTED_CODES    = list(CURRENCY_META.keys())
COOKIE_NAME        = "preferred_currency"
SESSION_KEY        = "preferred_currency"
GEOIP_CACHE_PREFIX = "geoip:country:"

# Country → currency mapping (common cases)
COUNTRY_CURRENCY = {
    "KE": "KES", "UG": "UGX", "TZ": "TZS",
    "US": "USD", "GB": "GBP",
    "DE": "EUR", "FR": "EUR", "IT": "EUR", "ES": "EUR",
    "AE": "AED", "SA": "AED",
    "AU": "AUD", "CA": "CAD",
}


class CurrencyMiddleware:
    """
    Attaches request.currency and request.currency_symbol.
    Detection order:
      1. Cookie (user's explicit choice — highest priority)
      2. Session
      3. IP geolocation (cached, non-blocking)
      4. Default: KES
    Never blocks page rendering.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.currency        = self._resolve_currency(request)
        request.currency_symbol = get_currency_symbol(request.currency)
        response = self.get_response(request)
        return response

    def _resolve_currency(self, request) -> str:
        # 1. Cookie
        cookie_val = request.COOKIES.get(COOKIE_NAME, "").upper()
        if cookie_val in SUPPORTED_CODES:
            return cookie_val

        # 2. Session
        session_val = request.session.get(SESSION_KEY, "").upper()
        if session_val in SUPPORTED_CODES:
            return session_val

        # 3. IP geolocation (only attempt on real IPs, not localhost)
        ip = self._get_client_ip(request)
        if ip and not _is_local_ip(ip):
            country = self._get_country_for_ip(ip)
            if country:
                currency = COUNTRY_CURRENCY.get(country, "KES")
                if currency in SUPPORTED_CODES:
                    return currency

        # 4. Default
        return settings.DEALERSHIP_CURRENCY

    def _get_client_ip(self, request) -> str:
        forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "")

    def _get_country_for_ip(self, ip: str) -> str | None:
        """
        Look up country for IP. Result is cached per-IP for 24 hours.
        Returns None on any failure — never raises.
        """
        cache_key = f"{GEOIP_CACHE_PREFIX}{ip}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached or None  # "" stored as miss marker

        try:
            geoip_url = settings.GEOIP_API_URL
            resp = requests.get(
                f"{geoip_url}/{ip}/json/",
                timeout=2,
                headers={"Accept": "application/json"},
            )
            if resp.status_code == 200:
                country = resp.json().get("country_code", "")
                # Cache success for 24h, miss for 1h
                cache.set(cache_key, country or "", timeout=86400 if country else 3600)
                return country or None
        except Exception as e:
            logger.debug("GeoIP lookup failed for %s: %s", ip, e)
            cache.set(cache_key, "", timeout=3600)  # cache miss to avoid repeated calls

        return None


def _is_local_ip(ip: str) -> bool:
    return ip in ("127.0.0.1", "::1", "localhost") or ip.startswith("192.168.") or ip.startswith("10.")
"""
Centralized cache key management for vehicles.
All cache keys defined in one place — never scattered in views.
Cache invalidation must happen here whenever vehicles change.
"""
import logging
from django.core.cache import cache

logger = logging.getLogger(__name__)

# ── Cache timeouts ────────────────────────────────────────────────────────────
TIMEOUT_SHORT = 60        # 1 minute — frequently changing data
TIMEOUT_MEDIUM = 300       # 5 minutes — catalogue sections
TIMEOUT_LONG = 3600      # 1 hour — makes, categories (rarely change)
TIMEOUT_DAY = 86400     # 24 hours — static-ish content

# ── Cache key templates ───────────────────────────────────────────────────────
KEY_HOMEPAGE_FEATURED = "vehicles:homepage:featured"
KEY_HOMEPAGE_ARRIVALS = "vehicles:homepage:arrivals"
KEY_HOMEPAGE_OFFERS = "vehicles:homepage:offers"
KEY_ALL_MAKES = "vehicles:makes:all"
KEY_POPULAR_MAKES = "vehicles:makes:popular"
KEY_ALL_CATEGORIES = "vehicles:categories:all"
KEY_POPULAR_CATEGORIES = "vehicles:categories:popular"
KEY_VEHICLE_DETAIL = "vehicles:detail:{slug}"
KEY_VEHICLE_RELATED = "vehicles:related:{vehicle_id}"
KEY_CATALOGUE_META = "vehicles:catalogue:meta"
KEY_STATS_COUNTS = "vehicles:stats:counts"


# ── Getters with fallback pattern ────────────────────────────────────────────

def get_or_set(key: str, loader_fn, timeout: int):
    """
    Generic cache-aside pattern with safe fallback.
    If Redis is unavailable, calls loader_fn directly.
    """
    try:
        cached = cache.get(key)
        if cached is not None:
            return cached
        value = loader_fn()
        try:
            cache.set(key, value, timeout=timeout)
        except Exception:
            pass  # Cache write failure is non-fatal
        return value
    except Exception as e:
        logger.warning(
            "Cache get_or_set failed for %s: %s — falling back to DB", key, e)
        return loader_fn()


# ── Invalidation ──────────────────────────────────────────────────────────────

def invalidate_vehicle(vehicle_slug: str = None, vehicle_id: int = None):
    """
    Call this whenever a vehicle is created/updated/published/sold/etc.
    Clears all caches that could contain stale vehicle data.
    """
    keys_to_delete = [
        KEY_HOMEPAGE_FEATURED,
        KEY_HOMEPAGE_ARRIVALS,
        KEY_HOMEPAGE_OFFERS,
        KEY_CATALOGUE_META,
        KEY_STATS_COUNTS,
    ]
    if vehicle_slug:
        keys_to_delete.append(KEY_VEHICLE_DETAIL.format(slug=vehicle_slug))
    if vehicle_id:
        keys_to_delete.append(
            KEY_VEHICLE_RELATED.format(vehicle_id=vehicle_id))

    try:
        cache.delete_many(keys_to_delete)
        logger.debug("Cache invalidated: %s", keys_to_delete)
    except Exception as e:
        logger.warning("Cache invalidation failed: %s", e)


def invalidate_makes_categories():
    """Call when a make or category is added/changed."""
    try:
        cache.delete_many([
            KEY_ALL_MAKES, KEY_POPULAR_MAKES,
            KEY_ALL_CATEGORIES, KEY_POPULAR_CATEGORIES,
        ])
    except Exception as e:
        logger.warning("Make/category cache invalidation failed: %s", e)

from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache


def health_check(request):
    """Basic liveness probe."""
    return JsonResponse({"status": "ok"})


def readiness_check(request):
    """
    Readiness probe — verify DB and cache are reachable.
    Does NOT expose sensitive details.
    """
    checks = {}

    # Database
    try:
        connection.ensure_connection()
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "unavailable"

    # Cache
    try:
        cache.set("_ready_check", "1", timeout=5)
        checks["cache"] = "ok" if cache.get(
            "_ready_check") == "1" else "degraded"
    except Exception:
        checks["cache"] = "unavailable"

    all_ok = all(v == "ok" for v in checks.values())
    status = 200 if all_ok else 503
    return JsonResponse({"status": "ready" if all_ok else "degraded", **checks}, status=status)

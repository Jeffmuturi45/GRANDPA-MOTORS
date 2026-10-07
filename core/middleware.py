import logging
import time
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


class AnalyticsMiddleware(MiddlewareMixin):
    """
    Lightweight middleware that queues analytics tracking.
    Actual DB writes happen in Celery to avoid blocking requests.
    """

    EXCLUDED_PATHS = {
        "/health/", "/ready/", "/static/", "/media/",
        "/favicon.ico", "/__debug__/", "/admin/jsi18n/",
    }

    def process_response(self, request, response):
        path = request.path
        # Skip excluded paths and non-200/301/302 for static
        if any(path.startswith(p) for p in self.EXCLUDED_PATHS):
            return response
        if response.status_code in (301, 302):
            return response
        # Queue analytics asynchronously — never block the response
        try:
            from analytics.tasks import track_page_view
            track_page_view.delay(
                path=path,
                method=request.method,
                status_code=response.status_code,
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
                referer=request.META.get("HTTP_REFERER", ""),
                ip_hash=_hash_ip(request.META.get("REMOTE_ADDR", "")),
                session_key=request.session.session_key or "",
            )
        except Exception:
            # Analytics must NEVER break vehicle browsing
            pass
        return response


class SecurityHeadersMiddleware(MiddlewareMixin):
    """Add security headers to every response."""

    def process_response(self, request, response):
        response["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response["X-Content-Type-Options"] = "nosniff"
        # CSP is set in production settings / nginx
        return response


def _hash_ip(ip: str) -> str:
    """One-way hash of IP for privacy-safe analytics."""
    import hashlib
    return hashlib.sha256(ip.encode()).hexdigest()[:16]

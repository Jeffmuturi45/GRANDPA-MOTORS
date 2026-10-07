from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from .services import CURRENCY_META, get_all_rates

SUPPORTED_CODES = list(CURRENCY_META.keys())
COOKIE_NAME = "preferred_currency"
SESSION_KEY = "preferred_currency"


@require_POST
def set_currency(request):
    """
    Ajax endpoint — user picks a currency.
    Stores in both cookie and session.
    Returns updated rates for the client-side price display.
    """
    import json
    try:
        body = json.loads(request.body)
        code = body.get("currency", "").upper()
    except (json.JSONDecodeError, AttributeError):
        code = request.POST.get("currency", "").upper()

    if code not in SUPPORTED_CODES:
        return JsonResponse({"error": "Unsupported currency"}, status=400)

    from .services import get_currency_symbol
    response = JsonResponse({
        "currency": code,
        "symbol":   get_currency_symbol(code),
        "rates":    get_all_rates(),
    })
    response.set_cookie(
        COOKIE_NAME, code,
        max_age=365 * 24 * 3600,
        httponly=False,   # JS needs to read this for display
        samesite="Lax",
        secure=not __import__("django.conf", fromlist=[
                              "settings"]).settings.DEBUG,
    )
    request.session[SESSION_KEY] = code
    return response


def get_rates_json(request):
    """
    Public endpoint returning current rates as JSON.
    Used by Alpine.js for client-side approximate conversions.
    Cached heavily — safe to call frequently.
    """
    from django.views.decorators.cache import cache_control
    rates = get_all_rates()
    response = JsonResponse({
        "base":  "KES",
        "rates": rates,
    })
    response["Cache-Control"] = "public, max-age=3600"
    return response

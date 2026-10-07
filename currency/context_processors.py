from .services import get_supported_currencies, get_currency_symbol, CURRENCY_META


def currency_context(request):
    """Make currency info available in all templates."""
    current = getattr(request, "currency", "KES")
    return {
        "current_currency":        current,
        "current_currency_symbol": get_currency_symbol(current),
        "supported_currencies":    get_supported_currencies(),
    }

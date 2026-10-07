from .querysets import get_makes_for_nav, get_categories_for_nav


def navigation_context(request):
    """
    Inject makes and categories into every template for the nav menu.
    Both are Redis-cached — no DB hit on most requests.
    """
    try:
        return {
            "nav_makes":      get_makes_for_nav(),
            "nav_categories": get_categories_for_nav(),
        }
    except Exception:
        return {"nav_makes": [], "nav_categories": []}
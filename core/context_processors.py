from django.conf import settings


def site_settings(request):
    """Make dealership settings available in all templates."""
    return {
        "DEALERSHIP_NAME": settings.DEALERSHIP_NAME,
        "DEALERSHIP_PHONE": settings.DEALERSHIP_PHONE,
        "DEALERSHIP_EMAIL": settings.DEALERSHIP_EMAIL,
        "DEALERSHIP_LOCATION": settings.DEALERSHIP_LOCATION,
        "DEALERSHIP_SITE_URL": settings.DEALERSHIP_SITE_URL,
        "WHATSAPP_BUSINESS_NUMBER": settings.WHATSAPP_BUSINESS_NUMBER,
    }

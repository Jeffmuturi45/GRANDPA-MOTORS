from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.sitemaps.views import sitemap

urlpatterns = [
    path("admin/", admin.site.urls),

    # Public site
    path("", include("catalogue.urls")),
    path("vehicles/", include("vehicles.urls")),
    path("currency/", include("currency.urls")),

    # Admin dashboard (custom, not Django admin)
    path("dashboard/", include("administration.urls")),

    # Health
    path("health/", include("core.urls")),

    # Sitemaps — added in Phase 6
    # path("sitemap.xml", sitemap, {...}),
]

# Error handlers
from catalogue.views import handler404, handler500, handler403, handler429
handler404 = handler404
handler500 = handler500
handler403 = handler403

if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        path("__debug__/", include(debug_toolbar.urls))] + urlpatterns
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)

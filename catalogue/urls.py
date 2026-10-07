from django.urls import path
from . import views

app_name = "catalogue"

urlpatterns = [
    path("",                              views.homepage,         name="homepage"),
    path("vehicles/",                     views.vehicle_list,     name="vehicle_list"),
    path("makes/",                        views.by_make,          name="makes_list"),
    path("makes/<slug:make_slug>/",       views.by_make,          name="by_make"),
    path("categories/<slug:category_slug>/", views.by_category,   name="by_category"),
    path("about/",                        views.about,            name="about"),
    path("contact/",                      views.contact,          name="contact"),
    path("privacy/",                      views.privacy_policy,   name="privacy"),
    path("terms/",                        views.terms,            name="terms"),
    # AJAX: returns models for a given make slug
    path("api/models/", views.api_models_for_make, name="api_models_for_make"),
]
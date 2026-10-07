from django.urls import path
from . import views

app_name = "currency"

urlpatterns = [
    path("set/",   views.set_currency,    name="set"),
    path("rates/", views.get_rates_json,  name="rates"),
]
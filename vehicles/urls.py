from django.urls import path
from catalogue import views as catalogue_views

app_name = "vehicles"

urlpatterns = [
    path("<slug:slug>/", catalogue_views.vehicle_detail, name="detail"),
]
from django.urls import path
from . import views

app_name = "administration"

urlpatterns = [
    path("",                 views.dashboard,          name="dashboard"),
    path("analytics/",       views.analytics,           name="analytics"),
    path("api/chart/",       views.analytics_chart_api, name="chart_api"),
    path("api/kpis/",        views.analytics_kpi_api,   name="kpi_api"),
]

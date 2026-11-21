
from django.urls import path

from . import views


app_name = "reports"

urlpatterns = [
    path(
        "report_dashboard/",
        views.report_dashboard,
        name="report_dashboard"
    ),

    path(
        "export/orders/",
        views.export_orders_csv,
        name="export_orders_csv"
    ),
]

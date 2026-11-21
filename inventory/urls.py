
from django.urls import path

from . import views


app_name = "inventory"

urlpatterns = [

    path(
        "inventory_dashboard/",
        views.inventory_dashboard,
        name="inventory_dashboard"
    ),

    path(
        "list/",
        views.inventory_list,
        name="inventory_list"
    ),

    path(
        "product/<int:product_id>/",
        views.inventory_detail,
        name="inventory_detail"
    ),

    path(
        "product/<int:product_id>/transaction/",
        views.stock_transaction_create,
        name="stock_transaction_create"
    ),

    path(
        "product/<int:product_id>/update/",
        views.inventory_update,
        name="inventory_update"
    ),

    path(
        "transactions/",
        views.transaction_history,
        name="transaction_history"
    ),

]

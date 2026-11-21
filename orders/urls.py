
from django.urls import path

from . import views


app_name = "orders"


urlpatterns = [

    # Customer Checkout
    path(
        "checkout/<slug:slug>/",
        views.order_create,
        name="order_create"
    ),

    path(
        "success/<str:order_number>/",
        views.order_success,
        name="order_success"
    ),

    # Customer Orders
    path(
        "my-orders/",
        views.my_orders,
        name="my_orders"
    ),

    path(
        "detail/<str:order_number>/",
        views.order_detail,
        name="order_detail"
    ),

    path(
        "cancel/<str:order_number>/",
        views.order_cancel,
        name="order_cancel"
    ),

    # Manager Orders
    path(
        "manage/",
        views.manage_orders,
        name="manage_orders"
    ),

    path(
        "manage/<str:order_number>/",
        views.manage_order_detail,
        name="manage_order_detail"
    ),

    path(
        "manage/<str:order_number>/update-status/",
        views.update_order_status,
        name="update_order_status"
    ),
    path(
        "cart-checkout/", 
        views.cart_checkout, 
        name="cart_checkout"
    ),

    path(
        "manage/<str:order_number>/reopen/",
        views.reopen_cancelled_order,
        name="reopen_cancelled_order"
    ),
]

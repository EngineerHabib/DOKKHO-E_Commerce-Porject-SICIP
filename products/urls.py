
from django.urls import path

from . import views


app_name = "products"

urlpatterns = [

    path(
        "product_list/",
        views.product_list,
        name="product_list"
    ),

    path(
        "create/",
        views.product_create,
        name="product_create"
    ),

    path(
        "<int:pk>/update/",
        views.product_update,
        name="product_update"
    ),

    path(
        "<int:pk>/delete/",
        views.product_delete,
        name="product_delete"
    ),

    path(
        "<slug:slug>/",
        views.product_detail,
        name="product_detail"
    ),

]

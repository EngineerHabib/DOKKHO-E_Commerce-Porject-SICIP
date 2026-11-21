
from django.urls import path
from . import views

app_name = "purchases"

urlpatterns = [

    path(
        "purchase_list/",
        views.purchase_list,
        name="purchase_list"
    ),

    path(
        "create/",
        views.purchase_create,
        name="purchase_create"
    ),

    path(
        "<int:pk>/",
        views.purchase_detail,
        name="purchase_detail"
    ),

    path(
        "<int:pk>/edit/",
        views.purchase_update,
        name="purchase_update"
    ),

    path(
        "<int:pk>/mark-ordered/",
        views.purchase_mark_ordered,
        name="purchase_mark_ordered"
    ),

    path(
        "<int:pk>/receive/",
        views.purchase_receive,
        name="purchase_receive"
    ),

    path(
        "<int:pk>/cancel/",
        views.purchase_cancel,
        name="purchase_cancel"
    ),

]

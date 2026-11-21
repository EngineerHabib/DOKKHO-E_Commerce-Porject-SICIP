
from django.urls import path

from . import views


app_name = "reviews"

urlpatterns = [

    path(
        "product/<slug:slug>/create/",
        views.review_create,
        name="review_create"
    ),

    path(
        "product/<slug:slug>/edit/<int:review_id>/",
        views.review_update,
        name="review_update"
    ),

    path(
        "product/<slug:slug>/delete/<int:review_id>/",
        views.review_delete,
        name="review_delete"
    ),

]

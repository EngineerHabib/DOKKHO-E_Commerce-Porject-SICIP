
from django.urls import path
from . import views

app_name = "categories"

urlpatterns = [

    path(
        "category_list/",
        views.category_list,
        name="category_list"
    ),

    path(
        "add/",
        views.category_create,
        name="category_create"
    ),

    path(
        "edit/<int:pk>/",
        views.category_update,
        name="category_update"
    ),

    path(
        "delete/<int:pk>/",
        views.category_delete,
        name="category_delete"
    ),

]

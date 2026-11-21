
from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [

    # Authentication
    path('', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # User Management
    path(
        'users/',
        views.manage_users_view,
        name='manage_users'
    ),

    path(
        'users/create/',
        views.create_user_view,
        name='create_user'
    ),

    path(
        'users/<int:pk>/edit/',
        views.edit_user_view,
        name='edit_user'
    ),

    path(
        "users/<int:pk>/delete/",
        views.delete_user_view,
        name="delete_user"
    ),


    path(
        "users/<int:pk>/toggle-status/",
        views.toggle_user_status_view,
        name="toggle_user_status"
    ),


]

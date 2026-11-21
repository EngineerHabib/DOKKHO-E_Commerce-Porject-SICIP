
from django.urls import path
from . import views

app_name = "audit"

urlpatterns = [
    path(
        "activity_logs/",
        views.activity_logs,
        name="activity_logs"
    ),
]

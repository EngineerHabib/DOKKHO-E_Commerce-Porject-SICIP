from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),

    path("", include("home.urls")),

    path("", include("accounts.urls")),
    path("dashboard/", include("dashboard.urls")),
    path("categories/", include("categories.urls")),
    path("products/", include("products.urls")),
    path("inventory/", include("inventory.urls")),
    path("reviews/", include("reviews.urls")),
    path("orders/", include("orders.urls")),
    path("cart/", include("cart.urls")),
    path("suppliers/", include("suppliers.urls")),
    path("purchases/", include("purchases.urls")),
    path("reports/", include("reports.urls")),
    path("audit/", include("audit.urls")),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )
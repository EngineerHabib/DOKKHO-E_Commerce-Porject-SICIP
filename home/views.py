
from django.shortcuts import render
from django.db.models import Q

from categories.models import Category
from products.models import Product


def home_view(request):

    search_query = request.GET.get("q", "").strip()

    # Active Categories
    categories = Category.objects.filter(
        is_active=True
    ).order_by("name")[:8]

    # Active Products
    products = Product.objects.filter(
        is_active=True,
        category__is_active=True
    ).select_related("category")

    # Product Search
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(category__name__icontains=search_query) |
            Q(sku__icontains=search_query)
        )

    # Latest Products
    latest_products = products.order_by(
        "-created_at"
    )[:8]

    # Discount Products
    discount_products = products.filter(
        discount_percentage__gt=0
    ).order_by("-discount_percentage")[:8]

    context = {
        "categories": categories,
        "featured_products": latest_products,
        "latest_products": latest_products,
        "discount_products": discount_products,
        "search_query": search_query,
    }

    return render(
        request,
        "home/home.html",
        context
    )

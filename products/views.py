
from functools import wraps

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.views.decorators.http import require_POST
from django.db.models import (
    Q,
    Avg,
    Count,
    OuterRef,
    Subquery,
    IntegerField,
    Value,
)
from django.db.models.functions import Coalesce

from .models import Product
from .forms import ProductForm

from django.db import transaction
from inventory.models import Inventory, StockTransaction

from audit.models import AuditLog
from audit.utils import log_activity


ALLOWED_ROLES = [
    "super_admin",
    "admin",
    "inventory_manager",
]


# Product fields to track
def get_product_snapshot(product):
    return {
        "sku": product.sku,
        "name": product.name,
        "category": str(product.category),
        "price": str(product.price),
        "discount_percentage": str(product.discount_percentage),
        "is_active": product.is_active,
    }


# Product Manager Permission
def product_manager_required(view_func):

    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):

        if (
            request.user.is_superuser
            or request.user.role in ALLOWED_ROLES
        ):
            return view_func(request, *args, **kwargs)

        raise PermissionDenied(
            "You do not have permission to manage products."
        )

    return wrapper


# Common Product Query
def get_product_queryset():

    stock_subquery = Inventory.objects.filter(
        product=OuterRef("pk")
    ).values("quantity")[:1]

    return Product.objects.select_related(
        "category"
    ).annotate(

        average_rating=Avg(
            "reviews__rating",
            filter=Q(reviews__is_approved=True)
        ),

        total_reviews=Count(
            "reviews",
            filter=Q(reviews__is_approved=True),
            distinct=True
        ),

        stock_quantity=Coalesce(
            Subquery(
                stock_subquery,
                output_field=IntegerField()
            ),
            Value(0),
            output_field=IntegerField()
        )

    )


# Product List
def product_list(request):

    products = get_product_queryset()

    is_manager = (
        request.user.is_authenticated
        and (
            request.user.is_superuser
            or request.user.role in ALLOWED_ROLES
        )
    )

    if not is_manager:
        products = products.filter(is_active=True)

    search = request.GET.get("search", "").strip()

    if search:
        products = products.filter(
            Q(name__icontains=search)
            | Q(sku__icontains=search)
            | Q(category__name__icontains=search)
        )

    category_slug = request.GET.get(
        "category", ""
    ).strip()

    if category_slug:
        products = products.filter(
            category__slug=category_slug
        )

    context = {
        "products": products,
        "search": search,
        "category_slug": category_slug,
        "is_manager": is_manager,
        "title": "Products",
    }

    return render(
        request,
        "products/product_list.html",
        context
    )


# Product Details
def product_detail(request, slug):

    product = get_object_or_404(
        get_product_queryset(),
        slug=slug
    )

    is_manager = (
        request.user.is_authenticated
        and (
            request.user.is_superuser
            or request.user.role in ALLOWED_ROLES
        )
    )

    if not product.is_active and not is_manager:
        raise PermissionDenied(
            "This product is not available."
        )

    reviews = product.reviews.filter(
        is_approved=True
    ).select_related(
        "user"
    )

    own_review = None

    if request.user.is_authenticated:
        own_review = product.reviews.filter(
            user=request.user
        ).first()

    context = {
        "product": product,
        "is_manager": is_manager,
        "title": product.name,
        "reviews": reviews,
        "own_review": own_review,
    }

    return render(
        request,
        "products/product_detail.html",
        context
    )



# Create Product
@product_manager_required
def product_create(request):

    form = ProductForm(
        request.POST or None,
        request.FILES or None
    )

    if request.method == "POST" and form.is_valid():

        with transaction.atomic():

            product = form.save(commit=False)

            product.created_by = request.user
            product.updated_by = request.user

            product.save()

            # Initial inventory
            quantity = form.cleaned_data["quantity"]

            inventory = Inventory.objects.create(
                product=product,
                quantity=quantity
            )

            # Record initial stock
            if quantity > 0:

                StockTransaction.objects.create(
                    inventory=inventory,
                    transaction_type=(
                        StockTransaction.TransactionType.STOCK_IN
                    ),
                    quantity=quantity,
                    previous_quantity=0,
                    new_quantity=quantity,
                    note="Initial stock during product creation.",
                    created_by=request.user
                )

            log_activity(
                request=request,
                action=AuditLog.Action.CREATE,
                description=(
                    f"Product created: {product.name}. "
                    f"SKU: {product.sku}. "
                    f"Initial Stock: {quantity}"
                ),
                instance=product,
            )

        messages.success(
            request,
            "Product created successfully."
        )

        return redirect("products:product_list")

    return render(
        request,
        "master/base_forms.html",
        {
            "form": form,
            "title": "Add New Product",
            "description": "Create a new product.",
            "button_text": "Save Product",
            "form_width": "col-md-8 col-lg-6",
        }
    )


# Update Product
@product_manager_required
def product_update(request, pk):

    product = get_object_or_404(
        Product,
        pk=pk
    )

    form = ProductForm(
        request.POST or None,
        request.FILES or None,
        instance=product
    )

    if request.method == "POST" and form.is_valid():

        with transaction.atomic():

            # Lock inventory to prevent concurrent stock updates
            inventory, created = (
                Inventory.objects.select_for_update().get_or_create(
                    product=product
                )
            )

            old_values = get_product_snapshot(product)

            old_quantity = inventory.quantity
            new_quantity = form.cleaned_data["quantity"]

            # Save product information
            product = form.save(commit=False)

            product.updated_by = request.user
            product.save()

            # Update inventory only when quantity changes
            if old_quantity != new_quantity:

                difference = abs(
                    new_quantity - old_quantity
                )

                if new_quantity > old_quantity:

                    transaction_type = (
                        StockTransaction.TransactionType.STOCK_IN
                    )

                    note = "Stock increased through product update."

                else:

                    transaction_type = (
                        StockTransaction.TransactionType.STOCK_OUT
                    )

                    note = "Stock decreased through product update."

                inventory.quantity = new_quantity

                inventory.save(
                    update_fields=[
                        "quantity",
                        "updated_at"
                    ]
                )

                # Record stock transaction
                StockTransaction.objects.create(
                    inventory=inventory,
                    transaction_type=transaction_type,
                    quantity=difference,
                    previous_quantity=old_quantity,
                    new_quantity=new_quantity,
                    note=note,
                    created_by=request.user
                )

            # Product change tracking
            new_values = get_product_snapshot(product)

            changes = []

            for field, old_value in old_values.items():

                new_value = new_values[field]

                if old_value != new_value:

                    changes.append(
                        f"{field}: {old_value} -> {new_value}"
                    )

            if old_quantity != new_quantity:

                changes.append(
                    f"quantity: {old_quantity} -> {new_quantity}"
                )

            if changes:

                log_activity(
                    request=request,
                    action=AuditLog.Action.UPDATE,
                    description=(
                        f"Product updated: {product.name}. "
                        f"Changes: {'; '.join(changes)}"
                    ),
                    instance=product,
                )

        messages.success(
            request,
            "Product and inventory updated successfully."
        )

        return redirect("products:product_list")

    return render(
        request,
        "master/base_forms.html",
        {
            "form": form,
            "title": "Update Product",
            "description": "Update product information and stock quantity.",
            "button_text": "Update Product",
            "form_width": "col-md-8 col-lg-6",
        }
    )


# Delete Product
@product_manager_required
@require_POST
def product_delete(request, pk):

    product = get_object_or_404(
        Product,
        pk=pk
    )

    product_name = product.name
    product_sku = product.sku

    # Log before deleting the product
    log_activity(
        request=request,
        action=AuditLog.Action.DELETE,
        description=(
            f"Product deleted: {product_name}. "
            f"SKU: {product_sku}"
        ),
        instance=product,
    )

    product.delete()

    messages.success(
        request,
        "Product deleted successfully."
    )

    return redirect("products:product_list")

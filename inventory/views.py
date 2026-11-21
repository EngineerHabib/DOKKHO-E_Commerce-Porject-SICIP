
from functools import wraps

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q, F
from django.views.decorators.http import require_POST

from products.models import Product
from .models import Inventory, StockTransaction
from .forms import StockTransactionForm, InventoryForm

from audit.models import AuditLog
from audit.utils import log_activity


ALLOWED_ROLES = [
    "super_admin",
    "admin",
    "inventory_manager",
]


# Inventory Manager Permission
def inventory_manager_required(view_func):

    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):

        if (
            request.user.is_superuser
            or request.user.role in ALLOWED_ROLES
        ):
            return view_func(request, *args, **kwargs)

        raise PermissionDenied(
            "You do not have permission to manage inventory."
        )

    return wrapper


# Inventory Dashboard
@inventory_manager_required
def inventory_dashboard(request):

    total_products = Inventory.objects.count()

    low_stock_count = Inventory.objects.filter(
        quantity__gt=0,
        quantity__lte=F("low_stock_threshold")
    ).count()

    out_of_stock_count = Inventory.objects.filter(
        quantity=0
    ).count()

    total_transactions = StockTransaction.objects.count()

    recent_transactions = (
        StockTransaction.objects
        .select_related(
            "inventory__product",
            "created_by"
        )
        .order_by("-created_at")[:10]
    )

    context = {
        "total_products": total_products,
        "low_stock_count": low_stock_count,
        "out_of_stock_count": out_of_stock_count,
        "total_transactions": total_transactions,
        "recent_transactions": recent_transactions,
        "title": "Inventory Dashboard",
    }

    return render(
        request,
        "inventory/inventory_dashboard.html",
        context
    )


# Inventory List
@inventory_manager_required
def inventory_list(request):

    inventories = Inventory.objects.select_related(
        "product",
        "product__category"
    )

    search = request.GET.get("search", "").strip()
    status = request.GET.get("status", "").strip()

    if search:
        inventories = inventories.filter(
            Q(product__name__icontains=search)
            | Q(product__sku__icontains=search)
        )

    if status == "low":
        inventories = inventories.filter(
            quantity__gt=0,
            quantity__lte=F("low_stock_threshold")
        )

    elif status == "out":
        inventories = inventories.filter(
            quantity=0
        )

    elif status == "available":
        inventories = inventories.filter(
            quantity__gt=F("low_stock_threshold")
        )

    context = {
        "inventories": inventories,
        "search": search,
        "status": status,
        "title": "Inventory List",
    }

    return render(
        request,
        "inventory/inventory_list.html",
        context
    )


# Inventory Details
@inventory_manager_required
def inventory_detail(request, product_id):

    product = get_object_or_404(
        Product,
        pk=product_id
    )

    inventory, created = Inventory.objects.get_or_create(
        product=product
    )

    transactions = inventory.transactions.select_related(
        "created_by"
    ).order_by("-created_at")

    context = {
        "product": product,
        "inventory": inventory,
        "transactions": transactions,
        "title": "Inventory Details",
    }

    return render(
        request,
        "inventory/inventory_detail.html",
        context
    )


# Stock In / Stock Out / Stock Adjustment
@inventory_manager_required
def stock_transaction_create(request, product_id):

    product = get_object_or_404(
        Product,
        pk=product_id
    )

    inventory, created = Inventory.objects.get_or_create(
        product=product
    )

    form = StockTransactionForm(
        request.POST or None
    )

    if request.method == "POST" and form.is_valid():

        transaction_type = form.cleaned_data[
            "transaction_type"
        ]

        quantity = form.cleaned_data["quantity"]

        with transaction.atomic():

            inventory = Inventory.objects.select_for_update().get(
                pk=inventory.pk
            )

            previous_quantity = inventory.quantity

            if transaction_type == StockTransaction.TransactionType.STOCK_IN:

                new_quantity = previous_quantity + quantity

            elif transaction_type == StockTransaction.TransactionType.STOCK_OUT:

                if quantity > previous_quantity:

                    form.add_error(
                        "quantity",
                        "Insufficient stock available."
                    )

                    return render(
                        request,
                        "inventory/stock_transaction_form.html",
                        {
                            "form": form,
                            "product": product,
                            "inventory": inventory,
                            "title": "Manage Stock",
                        }
                    )

                new_quantity = previous_quantity - quantity

            else:
                # Adjustment means setting the actual stock quantity.
                new_quantity = quantity

            inventory.quantity = new_quantity
            inventory.save(
                update_fields=["quantity", "updated_at"]
            )

            stock_transaction = StockTransaction.objects.create(
                inventory=inventory,
                transaction_type=transaction_type,
                quantity=quantity,
                previous_quantity=previous_quantity,
                new_quantity=new_quantity,
                note=form.cleaned_data["note"],
                created_by=request.user,
            )

            # Audit stock transaction
            log_activity(
                request=request,
                action=AuditLog.Action.CREATE,
                description=(
                    f"Stock {transaction_type} for "
                    f"{product.name} (SKU: {product.sku}). "
                    f"Previous quantity: {previous_quantity}. "
                    f"Transaction quantity: {quantity}. "
                    f"New quantity: {new_quantity}. "
                    f"Note: {form.cleaned_data['note']}"
                ),
                instance=stock_transaction,
            )

        messages.success(
            request,
            "Stock updated successfully."
        )

        return redirect(
            "inventory:inventory_detail",
            product_id=product.pk
        )

    context = {
        "form": form,
        "product": product,
        "inventory": inventory,
        "title": "Manage Stock",
    }

    return render(
        request,
        "inventory/stock_transaction_form.html",
        context
    )


# Update Low Stock Threshold
@inventory_manager_required
def inventory_update(request, product_id):

    product = get_object_or_404(
        Product,
        pk=product_id
    )

    inventory, created = Inventory.objects.get_or_create(
        product=product
    )

    form = InventoryForm(
        request.POST or None,
        instance=inventory
    )

    if request.method == "POST" and form.is_valid():

        old_quantity = inventory.quantity
        old_threshold = inventory.low_stock_threshold

        inventory = form.save()

        changes = []

        if old_quantity != inventory.quantity:
            changes.append(
                f"quantity: {old_quantity} -> {inventory.quantity}"
            )

        if old_threshold != inventory.low_stock_threshold:
            changes.append(
                f"low_stock_threshold: "
                f"{old_threshold} -> {inventory.low_stock_threshold}"
            )

        if changes:
            log_activity(
                request=request,
                action=AuditLog.Action.UPDATE,
                description=(
                    f"Inventory settings updated for "
                    f"{product.name} (SKU: {product.sku}). "
                    f"Changes: {'; '.join(changes)}"
                ),
                instance=inventory,
            )

        messages.success(
            request,
            "Inventory settings updated successfully."
        )

        return redirect(
            "inventory:inventory_detail",
            product_id=product.pk
        )

    context = {
        "form": form,
        "product": product,
        "inventory": inventory,
        "title": "Update Inventory Settings",
    }

    return render(
        request,
        "inventory/inventory_update.html",
        context
    )


# Stock Transaction History
@inventory_manager_required
def transaction_history(request):

    transactions = StockTransaction.objects.select_related(
        "inventory__product",
        "created_by"
    )

    search = request.GET.get("search", "").strip()
    transaction_type = request.GET.get(
        "transaction_type",
        ""
    ).strip()

    if search:
        transactions = transactions.filter(
            Q(inventory__product__name__icontains=search)
            | Q(inventory__product__sku__icontains=search)
        )

    if transaction_type:
        transactions = transactions.filter(
            transaction_type=transaction_type
        )

    context = {
        "transactions": transactions,
        "search": search,
        "transaction_type": transaction_type,
        "transaction_types": StockTransaction.TransactionType.choices,
        "title": "Stock Transaction History",
    }

    return render(
        request,
        "inventory/transaction_history.html",
        context
    )


from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseForbidden
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Purchase
from .forms import PurchaseForm, PurchaseItemFormSet

from inventory.models import Inventory, StockTransaction

from audit.models import AuditLog
from audit.utils import log_activity


ALLOWED_ROLES = [
    "super_admin",
    "admin",
    "inventory_manager",
]


def purchase_manager_required(view_func):

    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):

        if not (
            request.user.is_superuser
            or request.user.role in ALLOWED_ROLES
        ):
            return HttpResponseForbidden(
                "You do not have permission to access this page."
            )

        return view_func(request, *args, **kwargs)

    return wrapper


def get_purchase_snapshot(purchase):

    return {
        "supplier": purchase.supplier_id,
        "expected_delivery_date": purchase.expected_delivery_date,
        "notes": purchase.notes,
        "status": purchase.status,
    }


def get_purchase_items_snapshot(purchase):

    return {
        item.product_id: {
            "product": item.product.name,
            "quantity": item.quantity,
            "unit_cost": str(item.unit_cost),
        }
        for item in purchase.items.select_related("product").all()
    }


@purchase_manager_required
def purchase_list(request):

    purchases = Purchase.objects.select_related(
        "supplier",
        "created_by"
    ).prefetch_related(
        "items"
    )

    search = request.GET.get("search", "").strip()
    status = request.GET.get("status", "").strip()

    if search:
        from django.db.models import Q

        purchases = purchases.filter(
            Q(purchase_number__icontains=search)
            | Q(supplier__company_name__icontains=search)
        )

    valid_statuses = Purchase.Status.values

    if status in valid_statuses:
        purchases = purchases.filter(status=status)

    context = {
        "purchases": purchases,
        "search": search,
        "selected_status": status,
        "status_choices": Purchase.Status.choices,
        "title": "Purchase Management",
    }

    return render(
        request,
        "purchases/purchase_list.html",
        context
    )


@purchase_manager_required
def purchase_create(request):

    if request.method == "POST":

        form = PurchaseForm(request.POST)

        if form.is_valid():

            with transaction.atomic():

                purchase = form.save(commit=False)
                purchase.created_by = request.user
                purchase.save()

                formset = PurchaseItemFormSet(
                    request.POST,
                    instance=purchase
                )

                if formset.is_valid():

                    formset.save()

                    log_activity(
                        request=request,
                        action=AuditLog.Action.CREATE,
                        description=(
                            f"Purchase created: "
                            f"{purchase.purchase_number}. "
                            f"Supplier: {purchase.supplier.company_name}. "
                            f"Items: {purchase.total_items}. "
                            f"Total quantity: {purchase.total_quantity}."
                        ),
                        instance=purchase,
                    )

                    messages.success(
                        request,
                        "Purchase created successfully."
                    )

                    return redirect(
                        "purchases:purchase_detail",
                        pk=purchase.pk
                    )

                purchase.delete()

        else:
            formset = PurchaseItemFormSet(request.POST)

    else:

        form = PurchaseForm()
        formset = PurchaseItemFormSet()

    context = {
        "form": form,
        "formset": formset,
        "title": "Create Purchase",
        "description": "Create a new supplier purchase.",
        "button_text": "Create Purchase",
        "cancel_url": "/purchases/",
    }

    return render(
        request,
        "purchases/purchase_form.html",
        context
    )


@purchase_manager_required
def purchase_detail(request, pk):

    purchase = get_object_or_404(
        Purchase.objects.select_related(
            "supplier",
            "created_by",
            "updated_by"
        ).prefetch_related(
            "items__product"
        ),
        pk=pk
    )

    context = {
        "purchase": purchase,
        "items": purchase.items.all(),
        "title": "Purchase Details",
    }

    return render(
        request,
        "purchases/purchase_detail.html",
        context
    )


@purchase_manager_required
def purchase_update(request, pk):

    purchase = get_object_or_404(
        Purchase,
        pk=pk
    )

    if purchase.status != Purchase.Status.DRAFT:

        messages.error(
            request,
            "Only draft purchases can be edited."
        )

        return redirect(
            "purchases:purchase_detail",
            pk=purchase.pk
        )

    if request.method == "POST":

        form = PurchaseForm(
            request.POST,
            instance=purchase
        )

        formset = PurchaseItemFormSet(
            request.POST,
            instance=purchase
        )

        if form.is_valid() and formset.is_valid():

            with transaction.atomic():

                old_purchase = get_purchase_snapshot(purchase)
                old_items = get_purchase_items_snapshot(purchase)

                updated_purchase = form.save(commit=False)
                updated_purchase.updated_by = request.user
                updated_purchase.save()

                formset.save()

                new_purchase = get_purchase_snapshot(updated_purchase)
                new_items = get_purchase_items_snapshot(updated_purchase)

                changes = []

                for field, old_value in old_purchase.items():

                    new_value = new_purchase[field]

                    if old_value != new_value:
                        changes.append(
                            f"{field} changed"
                        )

                added_products = set(new_items) - set(old_items)
                removed_products = set(old_items) - set(new_items)

                changed_products = [
                    product_id
                    for product_id in set(old_items) & set(new_items)
                    if old_items[product_id] != new_items[product_id]
                ]

                if added_products:
                    changes.append(
                        f"{len(added_products)} product(s) added"
                    )

                if removed_products:
                    changes.append(
                        f"{len(removed_products)} product(s) removed"
                    )

                if changed_products:
                    changes.append(
                        f"{len(changed_products)} product(s) updated"
                    )

                if changes:

                    log_activity(
                        request=request,
                        action=AuditLog.Action.UPDATE,
                        description=(
                            f"Purchase updated: "
                            f"{purchase.purchase_number}. "
                            f"Changes: {', '.join(changes)}."
                        ),
                        instance=updated_purchase,
                    )

            messages.success(
                request,
                "Purchase updated successfully."
            )

            return redirect(
                "purchases:purchase_detail",
                pk=purchase.pk
            )

    else:

        form = PurchaseForm(instance=purchase)

        formset = PurchaseItemFormSet(
            instance=purchase
        )

    context = {
        "form": form,
        "formset": formset,
        "purchase": purchase,
        "title": "Update Purchase",
        "description": "Update your draft purchase.",
        "button_text": "Update Purchase",
        "cancel_url": f"/purchases/{purchase.pk}/",
    }

    return render(
        request,
        "purchases/purchase_form.html",
        context
    )


@purchase_manager_required
@require_POST
def purchase_mark_ordered(request, pk):

    with transaction.atomic():

        purchase = get_object_or_404(
            Purchase.objects.select_for_update(),
            pk=pk
        )

        if purchase.status != Purchase.Status.DRAFT:

            messages.error(
                request,
                "Only draft purchases can be marked as ordered."
            )

            return redirect(
                "purchases:purchase_detail",
                pk=purchase.pk
            )

        if not purchase.items.exists():

            messages.error(
                request,
                "Add at least one product before ordering."
            )

            return redirect(
                "purchases:purchase_detail",
                pk=purchase.pk
            )

        purchase.status = Purchase.Status.ORDERED
        purchase.updated_by = request.user

        purchase.save(
            update_fields=[
                "status",
                "updated_by",
                "updated_at",
            ]
        )

        log_activity(
            request=request,
            action=AuditLog.Action.UPDATE,
            description=(
                f"Purchase marked as ORDERED: "
                f"{purchase.purchase_number}."
            ),
            instance=purchase,
        )

    messages.success(
        request,
        "Purchase marked as ordered successfully."
    )

    return redirect(
        "purchases:purchase_detail",
        pk=purchase.pk
    )


@purchase_manager_required
@require_POST
def purchase_receive(request, pk):

    with transaction.atomic():

        purchase = get_object_or_404(
            Purchase.objects.select_for_update(),
            pk=pk
        )

        if purchase.status != Purchase.Status.ORDERED:

            messages.error(
                request,
                "Only ordered purchases can be received."
            )

            return redirect(
                "purchases:purchase_detail",
                pk=purchase.pk
            )

        items = list(
            purchase.items.select_related(
                "product"
            ).order_by("id")
        )

        if not items:

            messages.error(
                request,
                "This purchase has no products."
            )

            return redirect(
                "purchases:purchase_detail",
                pk=purchase.pk
            )

        for item in items:

            inventory, created = Inventory.objects.get_or_create(
                product=item.product,
                defaults={
                    "quantity": 0,
                }
            )

            if created:

                log_activity(
                    request=request,
                    action=AuditLog.Action.CREATE,
                    description=(
                        f"Inventory created during purchase receiving "
                        f"for product: {item.product.name}."
                    ),
                    instance=inventory,
                )

            inventory = Inventory.objects.select_for_update().get(
                pk=inventory.pk
            )

            previous_quantity = inventory.quantity

            inventory.quantity += item.quantity

            inventory.save(
                update_fields=[
                    "quantity",
                    "updated_at",
                ]
            )

            log_activity(
                request=request,
                action=AuditLog.Action.UPDATE,
                description=(
                    f"Inventory stock increased for "
                    f"{item.product.name}. "
                    f"Previous stock: {previous_quantity}. "
                    f"Received: {item.quantity}. "
                    f"New stock: {inventory.quantity}."
                ),
                instance=inventory,
            )

            stock_transaction = StockTransaction.objects.create(
                inventory=inventory,
                transaction_type=StockTransaction.TransactionType.STOCK_IN,
                quantity=item.quantity,
                previous_quantity=previous_quantity,
                new_quantity=inventory.quantity,
                note=f"Stock received from Purchase {purchase.purchase_number}",
                created_by=request.user,
            )

            log_activity(
                request=request,
                action=AuditLog.Action.CREATE,
                description=(
                    f"Stock IN transaction created from purchase "
                    f"{purchase.purchase_number}. "
                    f"Product: {item.product.name}. "
                    f"Quantity: {item.quantity}. "
                    f"Previous stock: {previous_quantity}. "
                    f"New stock: {inventory.quantity}."
                ),
                instance=stock_transaction,
            )

        purchase.status = Purchase.Status.RECEIVED
        purchase.received_at = timezone.now()
        purchase.updated_by = request.user

        purchase.save(
            update_fields=[
                "status",
                "received_at",
                "updated_by",
                "updated_at",
            ]
        )

        log_activity(
            request=request,
            action=AuditLog.Action.UPDATE,
            description=(
                f"Purchase received successfully: "
                f"{purchase.purchase_number}. "
                f"Inventory stock updated."
            ),
            instance=purchase,
        )

    messages.success(
        request,
        "Purchase received successfully. Inventory stock updated."
    )

    return redirect(
        "purchases:purchase_detail",
        pk=purchase.pk
    )


@purchase_manager_required
@require_POST
def purchase_cancel(request, pk):

    with transaction.atomic():

        purchase = get_object_or_404(
            Purchase.objects.select_for_update(),
            pk=pk
        )

        if purchase.status not in [
            Purchase.Status.DRAFT,
            Purchase.Status.ORDERED,
        ]:

            messages.error(
                request,
                "This purchase cannot be cancelled."
            )

            return redirect(
                "purchases:purchase_detail",
                pk=purchase.pk
            )

        purchase.status = Purchase.Status.CANCELLED
        purchase.updated_by = request.user

        purchase.save(
            update_fields=[
                "status",
                "updated_by",
                "updated_at",
            ]
        )

        log_activity(
            request=request,
            action=AuditLog.Action.UPDATE,
            description=(
                f"Purchase cancelled: "
                f"{purchase.purchase_number}."
            ),
            instance=purchase,
        )

    messages.success(
        request,
        "Purchase cancelled successfully."
    )

    return redirect(
        "purchases:purchase_detail",
        pk=purchase.pk
    )

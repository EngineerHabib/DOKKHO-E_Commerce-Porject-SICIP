
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views.decorators.http import require_POST

from .models import Supplier
from .forms import SupplierForm

from audit.models import AuditLog
from audit.utils import log_activity


MANAGER_ROLES = [
    "super_admin",
    "admin",
    "inventory_manager",
]


# Supplier fields to track
def get_supplier_snapshot(supplier):
    return {
        "company_name": supplier.company_name,
        "contact_person": supplier.contact_person,
        "email": supplier.email,
        "phone": supplier.phone,
        "alternate_phone": supplier.alternate_phone,
        "address": supplier.address,
        "city": supplier.city,
        "country": supplier.country,
        "notes": supplier.notes,
        "is_active": supplier.is_active,
    }


def supplier_manager_required(view_func):

    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):

        if (
            request.user.is_superuser
            or request.user.role in MANAGER_ROLES
        ):
            return view_func(request, *args, **kwargs)

        raise PermissionDenied(
            "You do not have permission to manage suppliers."
        )

    return wrapper


# Supplier List
@supplier_manager_required
def supplier_list(request):

    suppliers = Supplier.objects.all()

    search = request.GET.get("search", "").strip()
    status = request.GET.get("status", "")

    if search:
        suppliers = suppliers.filter(
            Q(company_name__icontains=search)
            | Q(contact_person__icontains=search)
            | Q(email__icontains=search)
            | Q(phone__icontains=search)
            | Q(city__icontains=search)
        )

    if status == "active":
        suppliers = suppliers.filter(is_active=True)

    elif status == "inactive":
        suppliers = suppliers.filter(is_active=False)

    context = {
        "suppliers": suppliers,
        "search": search,
        "status": status,
        "total_suppliers": Supplier.objects.count(),
        "active_suppliers": Supplier.objects.filter(is_active=True).count(),
        "inactive_suppliers": Supplier.objects.filter(is_active=False).count(),
    }

    return render(
        request,
        "suppliers/supplier_list.html",
        context
    )


# Supplier Details
@supplier_manager_required
def supplier_detail(request, pk):

    supplier = get_object_or_404(
        Supplier,
        pk=pk
    )

    return render(
        request,
        "suppliers/supplier_detail.html",
        {"supplier": supplier}
    )


# Create Supplier
@supplier_manager_required
def supplier_create(request):

    if request.method == "POST":
        form = SupplierForm(request.POST)

        if form.is_valid():

            supplier = form.save(commit=False)
            supplier.created_by = request.user
            supplier.save()

            log_activity(
                request=request,
                action=AuditLog.Action.CREATE,
                description=(
                    f"Supplier created: {supplier.company_name}. "
                    f"Contact: {supplier.contact_person}"
                ),
                instance=supplier,
            )

            messages.success(
                request,
                "Supplier added successfully."
            )

            return redirect(
                "suppliers:supplier_detail",
                pk=supplier.pk
            )

    else:
        form = SupplierForm()

    return render(
        request,
        "master/base_forms.html",
        {
            "form": form,
            "title": "Add New Supplier",
            "description": "Add a new supplier to SmartCommerce.",
            "button_text": "Save Supplier",
            "form_width": "col-md-8 col-lg-7",
            "cancel_url": reverse("suppliers:supplier_list"),
        }
    )


# Update Supplier
@supplier_manager_required
def supplier_update(request, pk):

    supplier = get_object_or_404(
        Supplier,
        pk=pk
    )

    if request.method == "POST":
        form = SupplierForm(
            request.POST,
            instance=supplier
        )

        if form.is_valid():

            old_values = get_supplier_snapshot(supplier)

            supplier = form.save()

            new_values = get_supplier_snapshot(supplier)

            changes = []

            for field, old_value in old_values.items():
                new_value = new_values[field]

                if old_value != new_value:
                    changes.append(
                        f"{field}: {old_value} -> {new_value}"
                    )

            if changes:
                log_activity(
                    request=request,
                    action=AuditLog.Action.UPDATE,
                    description=(
                        f"Supplier updated: {supplier.company_name}. "
                        f"Changes: {'; '.join(changes)}"
                    ),
                    instance=supplier,
                )

            messages.success(
                request,
                "Supplier updated successfully."
            )

            return redirect(
                "suppliers:supplier_detail",
                pk=supplier.pk
            )

    else:
        form = SupplierForm(instance=supplier)

    return render(
        request,
        "master/base_forms.html",
        {
            "form": form,
            "title": "Update Supplier",
            "description": f"Update information for {supplier.company_name}.",
            "button_text": "Update Supplier",
            "form_width": "col-md-8 col-lg-7",
            "cancel_url": reverse(
                "suppliers:supplier_detail",
                kwargs={"pk": supplier.pk}
            ),
        }
    )


# Delete Supplier
@supplier_manager_required
@require_POST
def supplier_delete(request, pk):

    supplier = get_object_or_404(
        Supplier,
        pk=pk
    )

    supplier_name = supplier.company_name

    log_activity(
        request=request,
        action=AuditLog.Action.DELETE,
        description=(
            f"Supplier deleted: {supplier_name}"
        ),
        instance=supplier,
    )

    supplier.delete()

    messages.success(
        request,
        f"{supplier_name} deleted successfully."
    )

    return redirect("suppliers:supplier_list")

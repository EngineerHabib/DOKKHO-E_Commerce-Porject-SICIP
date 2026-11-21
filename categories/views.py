
from functools import wraps

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.views.decorators.http import require_POST

from .models import Category
from .forms import CategoryForm

from audit.models import AuditLog
from audit.utils import log_activity


# Roles allowed to manage categories
ALLOWED_ROLES = [
    "super_admin",
    "admin",
    "inventory_manager",
]


# Category fields to track
def get_category_snapshot(category):
    return {
        "name": category.name,
        "slug": category.slug,
        "description": category.description,
        "is_active": category.is_active,
    }


# Check Category Management Permission
def category_manager_required(view_func):

    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):

        if (
            request.user.is_superuser
            or request.user.role in ALLOWED_ROLES
        ):
            return view_func(request, *args, **kwargs)

        raise PermissionDenied(
            "You do not have permission to manage categories."
        )

    return wrapper


# Category List
def category_list(request):

    is_manager = (
        request.user.is_authenticated
        and (
            request.user.is_superuser
            or request.user.role in ALLOWED_ROLES
        )
    )

    categories = Category.objects.select_related(
        "created_by",
        "updated_by"
    )

    if not is_manager:
        categories = categories.filter(is_active=True)

    context = {
        "categories": categories,
        "title": "Categories",
        "is_manager": is_manager,
    }

    return render(
        request,
        "categories/category_list.html",
        context
    )


# Create Category
@category_manager_required
def category_create(request):

    form = CategoryForm(
        request.POST or None,
        request.FILES or None
    )

    if request.method == "POST" and form.is_valid():

        category = form.save(commit=False)

        category.created_by = request.user
        category.updated_by = request.user

        category.save()

        log_activity(
            request=request,
            action=AuditLog.Action.CREATE,
            description=(
                f"Category created: {category.name}"
            ),
            instance=category,
        )

        messages.success(
            request,
            "Category created successfully."
        )

        return redirect("categories:category_list")

    context = {
        "form": form,
        "title": "Add New Category",
        "description": "Create a new product category.",
        "button_text": "Save Category",
        "form_width": "col-md-8 col-lg-6",
    }

    return render(
        request,
        "master/base_forms.html",
        context
    )


# Update Category
@category_manager_required
def category_update(request, pk):

    category = get_object_or_404(
        Category,
        pk=pk
    )

    form = CategoryForm(
        request.POST or None,
        request.FILES or None,
        instance=category
    )

    if request.method == "POST" and form.is_valid():

        old_values = get_category_snapshot(category)

        category = form.save(commit=False)
        category.updated_by = request.user
        category.save()

        new_values = get_category_snapshot(category)

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
                    f"Category updated: {category.name}. "
                    f"Changes: {'; '.join(changes)}"
                ),
                instance=category,
            )

        messages.success(
            request,
            "Category updated successfully."
        )

        return redirect("categories:category_list")

    context = {
        "form": form,
        "title": "Update Category",
        "description": "Update category information.",
        "button_text": "Update Category",
        "form_width": "col-md-8 col-lg-6",
    }

    return render(
        request,
        "master/base_forms.html",
        context
    )


# Delete Category
@category_manager_required
@require_POST
def category_delete(request, pk):

    category = get_object_or_404(
        Category,
        pk=pk
    )

    category_name = category.name

    log_activity(
        request=request,
        action=AuditLog.Action.DELETE,
        description=(
            f"Category deleted: {category_name}"
        ),
        instance=category,
    )

    category.delete()

    messages.success(
        request,
        "Category deleted successfully."
    )

    return redirect("categories:category_list")

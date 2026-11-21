
from django.contrib import admin
from django.db import transaction

from .models import Purchase, PurchaseItem

from audit.models import AuditLog
from audit.utils import log_activity


class PurchaseItemInline(admin.TabularInline):

    model = PurchaseItem

    extra = 1

    autocomplete_fields = (
        "product",
    )

    fields = (
        "product",
        "quantity",
        "unit_cost",
    )

    readonly_fields = ()

    show_change_link = True


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):

    list_display = (
        "purchase_number",
        "supplier",
        "status",
        "purchase_date",
        "expected_delivery_date",
        "total_items",
        "total_quantity",
        "total_amount",
        "created_by",
        "created_at",
    )

    list_filter = (
        "status",
        "purchase_date",
        "expected_delivery_date",
        "created_at",
    )

    search_fields = (
        "purchase_number",
        "supplier__company_name",
        "supplier__contact_person",
    )

    autocomplete_fields = (
        "supplier",
    )

    readonly_fields = (
        "purchase_number",
        "purchase_date",
        "received_at",
        "created_by",
        "updated_by",
        "created_at",
        "updated_at",
        "total_items",
        "total_quantity",
        "total_amount",
    )

    inlines = (
        PurchaseItemInline,
    )

    date_hierarchy = "purchase_date"

    list_per_page = 25

    ordering = (
        "-created_at",
    )

    fieldsets = (
        ("Purchase Information", {
            "fields": (
                "purchase_number",
                "supplier",
                "status",
            )
        }),

        ("Delivery Information", {
            "fields": (
                "purchase_date",
                "expected_delivery_date",
                "received_at",
            )
        }),

        ("Purchase Summary", {
            "fields": (
                "total_items",
                "total_quantity",
                "total_amount",
            )
        }),

        ("Additional Information", {
            "fields": (
                "notes",
            )
        }),

        ("User Information", {
            "fields": (
                "created_by",
                "updated_by",
                "created_at",
                "updated_at",
            )
        }),
    )

    def save_model(self, request, obj, form, change):

        with transaction.atomic():

            if change:

                old_obj = Purchase.objects.get(
                    pk=obj.pk
                )

                old_data = {
                    "supplier": old_obj.supplier.company_name,
                    "status": old_obj.status,
                    "expected_delivery_date": old_obj.expected_delivery_date,
                    "notes": old_obj.notes,
                }

            else:
                old_data = None

            if not change:
                obj.created_by = request.user

            obj.updated_by = request.user

            super().save_model(
                request,
                obj,
                form,
                change
            )

            if change:

                new_data = {
                    "supplier": obj.supplier.company_name,
                    "status": obj.status,
                    "expected_delivery_date": obj.expected_delivery_date,
                    "notes": obj.notes,
                }

                changes = []

                for field, old_value in old_data.items():

                    new_value = new_data[field]

                    if old_value != new_value:

                        changes.append(
                            f"{field}: {old_value} -> {new_value}"
                        )

                if changes:

                    log_activity(
                        request=request,
                        action=AuditLog.Action.UPDATE,
                        description=(
                            f"Purchase updated from Admin: "
                            f"{obj.purchase_number}. "
                            f"Changes: {'; '.join(changes)}."
                        ),
                        instance=obj,
                    )

            else:

                log_activity(
                    request=request,
                    action=AuditLog.Action.CREATE,
                    description=(
                        f"Purchase created from Admin: "
                        f"{obj.purchase_number}. "
                        f"Supplier: {obj.supplier.company_name}."
                    ),
                    instance=obj,
                )

    def save_formset(self, request, form, formset, change):

        if formset.model != PurchaseItem:
            return super().save_formset(
                request,
                form,
                formset,
                change
            )

        with transaction.atomic():

            purchase = form.instance

            old_items = {
                item.product_id: {
                    "product": item.product.name,
                    "quantity": item.quantity,
                    "unit_cost": str(item.unit_cost),
                }
                for item in purchase.items.select_related(
                    "product"
                ).all()
            }

            instances = formset.save(commit=False)

            for obj in formset.deleted_objects:
                obj.delete()

            for obj in instances:
                obj.save()

            formset.save_m2m()

            new_items = {
                item.product_id: {
                    "product": item.product.name,
                    "quantity": item.quantity,
                    "unit_cost": str(item.unit_cost),
                }
                for item in purchase.items.select_related(
                    "product"
                ).all()
            }

            changes = []

            added = set(new_items) - set(old_items)
            removed = set(old_items) - set(new_items)
            common = set(old_items) & set(new_items)

            for product_id in added:

                item = new_items[product_id]

                changes.append(
                    f"Product added: {item['product']}, "
                    f"Quantity: {item['quantity']}, "
                    f"Unit Cost: {item['unit_cost']}."
                )

            for product_id in removed:

                item = old_items[product_id]

                changes.append(
                    f"Product removed: {item['product']}."
                )

            for product_id in common:

                old_item = old_items[product_id]
                new_item = new_items[product_id]

                if old_item != new_item:

                    changes.append(
                        f"Product updated: {new_item['product']}. "
                        f"Old Qty: {old_item['quantity']}, "
                        f"New Qty: {new_item['quantity']}. "
                        f"Old Cost: {old_item['unit_cost']}, "
                        f"New Cost: {new_item['unit_cost']}."
                    )

            if changes:

                log_activity(
                    request=request,
                    action=(
                        AuditLog.Action.UPDATE
                        if change
                        else AuditLog.Action.CREATE
                    ),
                    description=(
                        f"Purchase items updated from Admin: "
                        f"{purchase.purchase_number}. "
                        f"Changes: {'; '.join(changes)}."
                    ),
                    instance=purchase,
                )

    def delete_model(self, request, obj):

        purchase_number = obj.purchase_number

        with transaction.atomic():

            super().delete_model(
                request,
                obj
            )

            log_activity(
                request=request,
                action=AuditLog.Action.DELETE,
                description=(
                    f"Purchase deleted from Admin: "
                    f"{purchase_number}."
                ),
                instance=None,
            )

    @admin.display(description="Total Items")
    def total_items(self, obj):
        return obj.total_items

    @admin.display(description="Total Quantity")
    def total_quantity(self, obj):
        return obj.total_quantity

    @admin.display(description="Total Amount")
    def total_amount(self, obj):
        return obj.total_amount


@admin.register(PurchaseItem)
class PurchaseItemAdmin(admin.ModelAdmin):

    list_display = (
        "purchase",
        "product",
        "quantity",
        "unit_cost",
        "line_total",
        "created_at",
    )

    list_filter = (
        "created_at",
    )

    search_fields = (
        "purchase__purchase_number",
        "product__name",
    )

    autocomplete_fields = (
        "purchase",
        "product",
    )

    readonly_fields = (
        "created_at",
        "line_total",
    )

    list_per_page = 25

    ordering = (
        "-id",
    )

    @admin.display(description="Line Total")
    def line_total(self, obj):
        return obj.line_total

    def save_model(self, request, obj, form, change):

        with transaction.atomic():

            if change:

                old_obj = PurchaseItem.objects.get(
                    pk=obj.pk
                )

                old_data = (
                    f"Product: {old_obj.product.name}, "
                    f"Quantity: {old_obj.quantity}, "
                    f"Unit Cost: {old_obj.unit_cost}"
                )

            else:
                old_data = None

            super().save_model(
                request,
                obj,
                form,
                change
            )

            if change:

                new_data = (
                    f"Product: {obj.product.name}, "
                    f"Quantity: {obj.quantity}, "
                    f"Unit Cost: {obj.unit_cost}"
                )

                if old_data != new_data:

                    log_activity(
                        request=request,
                        action=AuditLog.Action.UPDATE,
                        description=(
                            f"Purchase item updated from Admin. "
                            f"Purchase: {obj.purchase.purchase_number}. "
                            f"Old: {old_data}. "
                            f"New: {new_data}."
                        ),
                        instance=obj,
                    )

            else:

                log_activity(
                    request=request,
                    action=AuditLog.Action.CREATE,
                    description=(
                        f"Purchase item created from Admin. "
                        f"Purchase: {obj.purchase.purchase_number}. "
                        f"Product: {obj.product.name}. "
                        f"Quantity: {obj.quantity}. "
                        f"Unit Cost: {obj.unit_cost}."
                    ),
                    instance=obj,
                )

    def delete_model(self, request, obj):

        description = (
            f"Purchase item deleted from Admin. "
            f"Purchase: {obj.purchase.purchase_number}. "
            f"Product: {obj.product.name}. "
            f"Quantity: {obj.quantity}. "
            f"Unit Cost: {obj.unit_cost}."
        )

        with transaction.atomic():

            super().delete_model(
                request,
                obj
            )

            log_activity(
                request=request,
                action=AuditLog.Action.DELETE,
                description=description,
                instance=None,
            )

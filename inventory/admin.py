
from django.contrib import admin

from .models import Inventory, StockTransaction

from audit.models import AuditLog
from audit.utils import log_activity


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):

    list_display = (
        "product",
        "quantity",
        "low_stock_threshold",
        "stock_status",
        "updated_at",
    )

    search_fields = (
        "product__name",
        "product__sku",
    )

    list_filter = (
        "updated_at",
    )

    readonly_fields = (
        "quantity",
        "updated_at",
    )

    AUDIT_FIELDS = (
        "quantity",
        "low_stock_threshold",
    )

    def stock_status(self, obj):

        if obj.quantity == 0:
            return "Out of Stock"

        if obj.quantity <= obj.low_stock_threshold:
            return "Low Stock"

        return "Available"

    stock_status.short_description = "Stock Status"

    def save_model(self, request, obj, form, change):

        old_values = {}

        if change:
            old_inventory = Inventory.objects.get(pk=obj.pk)

            for field in self.AUDIT_FIELDS:
                old_values[field] = getattr(old_inventory, field)

        super().save_model(request, obj, form, change)

        if not change:

            log_activity(
                request=request,
                action=AuditLog.Action.CREATE,
                description=(
                    f"Inventory created through Admin for "
                    f"{obj.product.name}. "
                    f"Quantity: {obj.quantity}, "
                    f"Low stock threshold: {obj.low_stock_threshold}"
                ),
                instance=obj,
            )

        else:

            changes = []

            for field in self.AUDIT_FIELDS:
                old_value = old_values.get(field)
                new_value = getattr(obj, field)

                if old_value != new_value:
                    changes.append(
                        f"{field}: {old_value} -> {new_value}"
                    )

            if changes:
                log_activity(
                    request=request,
                    action=AuditLog.Action.UPDATE,
                    description=(
                        f"Inventory updated through Admin for "
                        f"{obj.product.name}. "
                        f"Changes: {'; '.join(changes)}"
                    ),
                    instance=obj,
                )

    def delete_model(self, request, obj):

        log_activity(
            request=request,
            action=AuditLog.Action.DELETE,
            description=(
                f"Inventory deleted through Admin for "
                f"{obj.product.name}. "
                f"Previous quantity: {obj.quantity}"
            ),
            instance=obj,
        )

        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):

        for obj in queryset.select_related("product").iterator():
            log_activity(
                request=request,
                action=AuditLog.Action.DELETE,
                description=(
                    f"Inventory deleted through Admin for "
                    f"{obj.product.name}. "
                    f"Previous quantity: {obj.quantity}"
                ),
                instance=obj,
            )

        super().delete_queryset(request, queryset)


@admin.register(StockTransaction)
class StockTransactionAdmin(admin.ModelAdmin):

    list_display = (
        "inventory",
        "transaction_type",
        "quantity",
        "previous_quantity",
        "new_quantity",
        "created_by",
        "created_at",
    )

    list_filter = (
        "transaction_type",
        "created_at",
    )

    search_fields = (
        "inventory__product__name",
        "inventory__product__sku",
        "note",
    )

    readonly_fields = (
        "inventory",
        "transaction_type",
        "quantity",
        "previous_quantity",
        "new_quantity",
        "note",
        "created_by",
        "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


from django.contrib import admin

from .models import Supplier

from audit.models import AuditLog
from audit.utils import log_activity


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):

    list_display = (
        "company_name",
        "contact_person",
        "phone",
        "email",
        "city",
        "is_active",
        "created_at",
    )

    list_filter = (
        "is_active",
        "country",
        "created_at",
    )

    search_fields = (
        "company_name",
        "contact_person",
        "email",
        "phone",
        "city",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    ordering = ("company_name",)

    AUDIT_FIELDS = (
        "company_name",
        "contact_person",
        "email",
        "phone",
        "alternate_phone",
        "address",
        "city",
        "country",
        "notes",
        "is_active",
    )

    def save_model(self, request, obj, form, change):

        old_values = {}

        if change:
            old_supplier = Supplier.objects.get(pk=obj.pk)

            for field in self.AUDIT_FIELDS:
                old_values[field] = getattr(old_supplier, field)

        super().save_model(request, obj, form, change)

        if not change:

            log_activity(
                request=request,
                action=AuditLog.Action.CREATE,
                description=(
                    f"Supplier created through Admin: "
                    f"{obj.company_name}"
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
                        f"Supplier updated through Admin: "
                        f"{obj.company_name}. "
                        f"Changes: {'; '.join(changes)}"
                    ),
                    instance=obj,
                )

    def delete_model(self, request, obj):

        log_activity(
            request=request,
            action=AuditLog.Action.DELETE,
            description=(
                f"Supplier deleted through Admin: "
                f"{obj.company_name}"
            ),
            instance=obj,
        )

        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):

        for obj in queryset.iterator():
            log_activity(
                request=request,
                action=AuditLog.Action.DELETE,
                description=(
                    f"Supplier deleted through Admin: "
                    f"{obj.company_name}"
                ),
                instance=obj,
            )

        super().delete_queryset(request, queryset)

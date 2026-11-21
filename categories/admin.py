
from django.contrib import admin

from .models import Category
from audit.models import AuditLog
from audit.utils import log_activity


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "slug",
        "is_active",
        "created_at",
    )

    list_filter = (
        "is_active",
        "created_at",
    )

    search_fields = (
        "name",
        "description",
    )

    prepopulated_fields = {
        "slug": ("name",)
    }

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    AUDIT_FIELDS = (
        "name",
        "slug",
        "description",
        "is_active",
    )

    def save_model(self, request, obj, form, change):

        old_values = {}

        if change:
            old_category = Category.objects.get(pk=obj.pk)

            for field in self.AUDIT_FIELDS:
                old_values[field] = getattr(old_category, field)

        super().save_model(request, obj, form, change)

        if not change:

            log_activity(
                request=request,
                action=AuditLog.Action.CREATE,
                description=(
                    f"Category created through Admin: {obj.name}"
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
                        f"Category updated through Admin: {obj.name}. "
                        f"Changes: {'; '.join(changes)}"
                    ),
                    instance=obj,
                )

    def delete_model(self, request, obj):

        log_activity(
            request=request,
            action=AuditLog.Action.DELETE,
            description=(
                f"Category deleted through Admin: {obj.name}"
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
                    f"Category deleted through Admin: {obj.name}"
                ),
                instance=obj,
            )

        super().delete_queryset(request, queryset)

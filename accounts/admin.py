
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User
from audit.models import AuditLog
from audit.utils import log_activity


@admin.register(User)
class CustomUserAdmin(UserAdmin):

    list_display = (
        "username",
        "email",
        "phone",
        "role",
        "is_active",
        "is_staff",
        "is_superuser",
    )

    list_filter = (
        "role",
        "is_active",
        "is_staff",
        "is_superuser",
    )

    search_fields = (
        "username",
        "email",
        "phone",
    )

    fieldsets = UserAdmin.fieldsets + (
        (
            "Additional Information",
            {
                "fields": (
                    "phone",
                    "role",
                    "profile_image",
                    "address",
                )
            }
        ),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        (
            "Additional Information",
            {
                "fields": (
                    "email",
                    "phone",
                    "role",
                    "profile_image",
                    "address",
                )
            }
        ),
    )

    # Important fields to track
    AUDIT_FIELDS = (
        "username",
        "email",
        "phone",
        "first_name",
        "last_name",
        "role",
        "is_active",
        "is_staff",
        "is_superuser",
    )

    def save_model(self, request, obj, form, change):

        old_values = {}

        if change:
            old_user = User.objects.get(pk=obj.pk)

            for field in self.AUDIT_FIELDS:
                old_values[field] = getattr(old_user, field)

        super().save_model(request, obj, form, change)

        if not change:
            log_activity(
                request=request,
                action=AuditLog.Action.CREATE,
                description=(
                    f"Admin created a user account: {obj.username}"
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
                        f"Admin updated user {obj.username}. "
                        f"Changes: {'; '.join(changes)}"
                    ),
                    instance=obj,
                )

    def delete_model(self, request, obj):

        log_activity(
            request=request,
            action=AuditLog.Action.DELETE,
            description=(
                f"Admin deleted user account: {obj.username}"
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
                    f"Admin deleted user account: {obj.username}"
                ),
                instance=obj,
            )

        super().delete_queryset(request, queryset)

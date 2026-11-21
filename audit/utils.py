
from .models import AuditLog


def get_client_ip(request):
    if not request:
        return None

    # Prefer REMOTE_ADDR; do not trust forwarded headers
    # unless your proxy is configured to sanitize them.
    return request.META.get("REMOTE_ADDR")


def log_activity(
    request,
    action,
    description,
    instance=None,
):
    user = None

    if request and request.user.is_authenticated:
        user = request.user

    app_label = ""
    model_name = ""
    object_id = ""
    object_repr = ""

    if instance is not None:
        app_label = instance._meta.app_label
        model_name = instance._meta.model_name
        object_id = str(instance.pk or "")
        object_repr = str(instance)[:255]

    return AuditLog.objects.create(
        user=user,
        action=action,
        app_label=app_label,
        model_name=model_name,
        object_id=object_id,
        object_repr=object_repr,
        description=description,
        ip_address=get_client_ip(request),
        user_agent=(
            request.META.get("HTTP_USER_AGENT", "")
            if request else ""
        ),
    )

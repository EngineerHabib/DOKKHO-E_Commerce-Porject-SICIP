
from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import render
from django.utils import timezone
from django.core.paginator import Paginator

from .models import AuditLog
from .forms import AuditFilterForm


AUDIT_MANAGER_ROLES = [
    "super_admin",
    "admin",
]


def audit_manager_required(view_func):

    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):

        allowed = (
            request.user.is_superuser
            or getattr(request.user, "role", None)
            in AUDIT_MANAGER_ROLES
        )

        if not allowed:
            raise PermissionDenied(
                "You do not have permission to access audit logs."
            )

        return view_func(request, *args, **kwargs)

    return wrapper


@audit_manager_required
def activity_logs(request):

    form = AuditFilterForm(request.GET or None)

    logs = AuditLog.objects.select_related("user").all()

    if request.GET and form.is_valid():

        search = form.cleaned_data.get("search")
        action = form.cleaned_data.get("action")
        start_date = form.cleaned_data.get("start_date")
        end_date = form.cleaned_data.get("end_date")

        if search:
            logs = logs.filter(
                Q(user__username__icontains=search)
                | Q(user__email__icontains=search)
                | Q(object_repr__icontains=search)
                | Q(description__icontains=search)
                | Q(app_label__icontains=search)
                | Q(model_name__icontains=search)
            )

        if action:
            logs = logs.filter(action=action)

        if start_date:
            logs = logs.filter(
                created_at__date__gte=start_date
            )

        if end_date:
            logs = logs.filter(
                created_at__date__lte=end_date
            )

    # Dashboard access tracking
    dashboard_logs = logs.filter(
        app_label="dashboard",
        model_name="Dashboard",
    )

    paginator = Paginator(logs, 25)
    page_obj = paginator.get_page(
        request.GET.get("page")
    )

    context = {
        "form": form,
        "page_obj": page_obj,

        # Overall Statistics
        "total_logs": logs.count(),

        "today_logs": AuditLog.objects.filter(
            created_at__date=timezone.localdate()
        ).count(),

        "create_count": AuditLog.objects.filter(
            action=AuditLog.Action.CREATE
        ).count(),

        "update_count": AuditLog.objects.filter(
            action=AuditLog.Action.UPDATE
        ).count(),

        "delete_count": AuditLog.objects.filter(
            action=AuditLog.Action.DELETE
        ).count(),

        # Dashboard Tracking Statistics
        "dashboard_access_count": dashboard_logs.count(),

        "today_dashboard_access": dashboard_logs.filter(
            created_at__date=timezone.localdate()
        ).count(),

        "dashboard_access_denied": dashboard_logs.filter(
            description__icontains="access denied"
        ).count(),
    }

    return render(
        request,
        "audit/activity_logs.html",
        context
    )

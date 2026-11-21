from functools import wraps
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.views.decorators.http import require_POST
from django.utils.http import url_has_allowed_host_and_scheme
from django.db.models.deletion import ProtectedError

from .models import User

from .forms import (
    RegistrationForm,
    LoginForm,
    UserManagementCreateForm,
    UserManagementUpdateForm,
)

from audit.models import AuditLog
from audit.utils import log_activity


# =====================================================
# USER REDIRECT
# =====================================================

def get_user_redirect_url(user):

    if user.is_superuser or user.role != "customer":
        return "dashboard:dashboard"

    return "home:home"


# =====================================================
# CUSTOMER REGISTRATION
# =====================================================

def register_view(request):

    if request.user.is_authenticated:
        return redirect(get_user_redirect_url(request.user))

    form = RegistrationForm(
        request.POST or None,
        request.FILES or None
    )

    if request.method == "POST" and form.is_valid():

        user = form.save(commit=False)

        # Public registration always creates Customer
        user.role = User.Role.CUSTOMER
        user.is_staff = False
        user.is_superuser = False

        user.save()

        log_activity(
            request=request,
            action=AuditLog.Action.CREATE,
            description=f"New customer account registered: {user.username}",
            instance=user,
        )

        messages.success(
            request,
            "Your account has been created successfully. Please login."
        )

        return redirect("accounts:login")

    context = {
        "form": form,
        "title": "Create Your Account",
        "description": "Register to get started with SmartCommerce.",
        "button_text": "Create Account",
        "form_width": "col-md-8 col-lg-6",
    }

    return render(
        request,
        "master/base_forms.html",
        context
    )


# =====================================================
# USER LOGIN
# =====================================================

def login_view(request):

    if request.user.is_authenticated:
        return redirect(get_user_redirect_url(request.user))

    form = LoginForm(
        request,
        data=request.POST or None
    )

    if request.method == "POST":

        if form.is_valid():

            user = form.get_user()

            login(request, user)

            log_activity(
                request=request,
                action=AuditLog.Action.LOGIN,
                description=f"User logged in successfully: {user.username}",
                instance=user,
            )

            messages.success(
                request,
                "Welcome back!"
            )

            next_url = (
                request.POST.get("next")
                or request.GET.get("next")
            )

            # Customers always go to Home Page
            if user.role == User.Role.CUSTOMER:
                return redirect("home:home")

            # Validate next URL to prevent open redirects
            if next_url and url_has_allowed_host_and_scheme(
                next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure()
            ):
                return redirect(next_url)

            return redirect(get_user_redirect_url(user))

        else:

            log_activity(
                request=request,
                action=AuditLog.Action.FAILED_LOGIN,
                description="Failed login attempt.",
            )

    context = {
        "form": form,
        "title": "Welcome Back",
        "description": "Login to your SmartCommerce account.",
        "button_text": "Login",
        "form_width": "col-md-7 col-lg-5",
    }

    return render(
        request,
        "master/base_forms.html",
        context
    )


# =====================================================
# USER LOGOUT
# =====================================================

@login_required
@require_POST
def logout_view(request):

    user = request.user

    log_activity(
        request=request,
        action=AuditLog.Action.LOGOUT,
        description=f"User logged out: {user.username}",
        instance=user,
    )

    logout(request)

    messages.success(
        request,
        "You have logged out successfully."
    )

    return redirect("accounts:login")


# =====================================================
# SUPER ADMIN PERMISSION DECORATOR
# =====================================================

def super_admin_required(view_func):

    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):

        if not (
            request.user.is_superuser
            or request.user.role == User.Role.SUPER_ADMIN
        ):
            raise PermissionDenied

        return view_func(request, *args, **kwargs)

    return wrapper


# =====================================================
# USER MANAGEMENT - ALL USERS
# =====================================================

@super_admin_required
def manage_users_view(request):

    users = User.objects.all().order_by("-date_joined")

    context = {
        "users": users,
        "title": "User Management",
        "active_users_count": User.objects.filter(is_active=True).count(),
        "inactive_users_count": User.objects.filter(is_active=False).count(),
    }

    return render(
        request,
        "manage_users.html",
        context
    )


# =====================================================
# USER MANAGEMENT - CREATE USER
# =====================================================

@super_admin_required
def create_user_view(request):

    form = UserManagementCreateForm(
        request.POST or None,
        request.FILES or None
    )

    if request.method == "POST" and form.is_valid():

        user = form.save()

        log_activity(
            request=request,
            action=AuditLog.Action.CREATE,
            description=f"User account created: {user.username}",
            instance=user,
        )

        messages.success(
            request,
            f"Account created successfully for {user.username}."
        )

        return redirect("accounts:manage_users")

    context = {
        "form": form,
        "title": "Create Account",
    }

    return render(
        request,
        "create_user.html",
        context
    )


# =====================================================
# USER MANAGEMENT - EDIT USER
# =====================================================

@super_admin_required
def edit_user_view(request, pk):

    user = get_object_or_404(
        User,
        pk=pk
    )

    # Protect Super Admin accounts
    if user.is_superuser or user.role == User.Role.SUPER_ADMIN:
        raise PermissionDenied

    form = UserManagementUpdateForm(
        request.POST or None,
        request.FILES or None,
        instance=user
    )

    if request.method == "POST" and form.is_valid():

        updated_user = form.save()

        log_activity(
            request=request,
            action=AuditLog.Action.UPDATE,
            description=f"User account updated: {updated_user.username}",
            instance=updated_user,
        )

        messages.success(
            request,
            f"Account updated successfully for {updated_user.username}."
        )

        return redirect("accounts:manage_users")

    context = {
        "form": form,
        "user_account": user,
        "title": "Edit User",
    }

    return render(
        request,
        "edit_user.html",
        context
    )


# =====================================================
# USER MANAGEMENT - DELETE USER
# =====================================================

@super_admin_required
@require_POST
def delete_user_view(request, pk):
    user = get_object_or_404(User, pk=pk)

    # Protect Super Admin
    if user.is_superuser or user.role == User.Role.SUPER_ADMIN:
        raise PermissionDenied

    # Prevent self-deletion
    if user.pk == request.user.pk:
        messages.error(request, "You cannot delete your own account.")
        return redirect("accounts:manage_users")

    username = user.username

    try:
        user.delete()

        messages.success(
            request,
            f"User '{username}' deleted successfully."
        )

    except ProtectedError:
        # Preserve order history and deactivate account
        user.is_active = False
        user.save(update_fields=["is_active"])

        messages.warning(
            request,
            f"'{username}' has existing records and cannot be deleted. "
            "The account has been deactivated instead."
        )

    return redirect("accounts:manage_users")



@super_admin_required
@require_POST
def toggle_user_status_view(request, pk):
    user = get_object_or_404(User, pk=pk)

    if user.is_superuser or user.role == User.Role.SUPER_ADMIN:
        raise PermissionDenied

    if user.pk == request.user.pk:
        messages.error(request, "You cannot deactivate your own account.")
        return redirect("accounts:manage_users")

    user.is_active = not user.is_active
    user.save(update_fields=["is_active"])

    if user.is_active:
        messages.success(
            request,
            f"{user.username} account activated successfully."
        )
    else:
        messages.success(
            request,
            f"{user.username} account deactivated successfully."
        )

    return redirect("accounts:manage_users")

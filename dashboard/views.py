
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import (
    Count,
    Sum,
    F,
    DecimalField,
    ExpressionWrapper,
)
from django.shortcuts import render, redirect

from accounts.models import User
from audit.models import AuditLog
from categories.models import Category
from products.models import Product
from orders.models import Order
from inventory.models import Inventory, StockTransaction
from purchases.models import Purchase
from suppliers.models import Supplier


MANAGEMENT_ROLES = [
    "super_admin",
    "admin",
    "inventory_manager",
    "order_manager",
]

ROLE_DASHBOARDS = {
    "super_admin": "Super Admin Dashboard",
    "admin": "Admin Dashboard",
    "inventory_manager": "Inventory Manager Dashboard",
    "order_manager": "Order Manager Dashboard",
    "customer": "Customer Dashboard",
}


def get_user_role(user):
    if user.is_superuser:
        return "super_admin"

    return getattr(user, "role", "customer") or "customer"


def track_dashboard_access(request, dashboard_name, role):
    AuditLog.objects.create(
        user=request.user,
        action=AuditLog.Action.OTHER,
        app_label="dashboard",
        model_name="Dashboard",
        object_repr=dashboard_name,
        description=(
            f"Dashboard accessed: {dashboard_name}. "
            f"User: {request.user.get_username()}. "
            f"Role: {role}."
        ),
        ip_address=request.META.get("REMOTE_ADDR"),
        user_agent=request.META.get("HTTP_USER_AGENT", ""),
    )


def get_purchase_total(queryset=None):
    if queryset is None:
        queryset = Purchase.objects.all()

    total = queryset.annotate(
        item_total=ExpressionWrapper(
            F("items__quantity") * F("items__unit_cost"),
            output_field=DecimalField(
                max_digits=14,
                decimal_places=2,
            ),
        )
    ).aggregate(
        total=Sum("item_total")
    )["total"]

    return total or Decimal("0.00")


@login_required
def dashboard_view(request):

    user = request.user
    role = get_user_role(user)

    if role not in ROLE_DASHBOARDS:
        return redirect("home:home")

    dashboard_name = ROLE_DASHBOARDS[role]
    is_management_user = role in MANAGEMENT_ROLES
    is_super_admin = role == "super_admin"
    is_admin = role == "admin"
    is_inventory_manager = role == "inventory_manager"
    is_order_manager = role == "order_manager"
    is_customer = role == "customer"

    display_name = user.get_full_name() or user.get_username()
    display_role = role.replace("_", " ").title()

    track_dashboard_access(request, dashboard_name, role)

    context = {
        "title": dashboard_name,
        "current_role": role,
        "display_name": display_name,
        "display_role": display_role,

        "is_management_user": is_management_user,
        "is_super_admin": is_super_admin,
        "is_admin": is_admin,
        "is_inventory_manager": is_inventory_manager,
        "is_order_manager": is_order_manager,
        "is_customer": is_customer,

        "has_dashboard_access": True,
    }

    # -------------------------------------------------
    # SUPER ADMIN / ADMIN: OVERALL BUSINESS DASHBOARD
    # -------------------------------------------------
    if is_super_admin or is_admin:

        context.update({
            # Users
            "total_users": User.objects.count(),
            "total_customers": User.objects.filter(
                role="customer",
                is_active=True,
            ).count(),
            "total_staff": User.objects.filter(
                role__in=MANAGEMENT_ROLES,
                is_active=True,
            ).count(),

            # Categories
            "total_categories": Category.objects.count(),
            "active_categories": Category.objects.filter(
                is_active=True
            ).count(),
            "inactive_categories": Category.objects.filter(
                is_active=False
            ).count(),

            # Products
            "total_products": Product.objects.count(),
            "active_products": Product.objects.filter(
                is_active=True
            ).count(),
            "inactive_products": Product.objects.filter(
                is_active=False
            ).count(),
            "discounted_products": Product.objects.filter(
                discount_percentage__gt=0,
                is_active=True,
            ).count(),

            # Orders
            "total_orders": Order.objects.count(),
            "pending_orders": Order.objects.filter(
                status=Order.Status.PENDING
            ).count(),
            "processing_orders": Order.objects.filter(
                status=Order.Status.PROCESSING
            ).count(),
            "delivered_orders": Order.objects.filter(
                status=Order.Status.DELIVERED
            ).count(),
            "cancelled_orders": Order.objects.filter(
                status=Order.Status.CANCELLED
            ).count(),

            # Revenue: only paid orders
            "paid_revenue": (
                Order.objects.filter(
                    payment_status=Order.PaymentStatus.PAID
                ).aggregate(total=Sum("total_amount"))["total"]
                or Decimal("0.00")
            ),

            # Suppliers
            "total_suppliers": Supplier.objects.count(),
            "active_suppliers": Supplier.objects.filter(
                is_active=True
            ).count(),

            # Inventory
            "total_inventory_items": Inventory.objects.count(),
            "total_stock_quantity": (
                Inventory.objects.aggregate(
                    total=Sum("quantity")
                )["total"] or 0
            ),
            "low_stock_count": Inventory.objects.filter(
                quantity__gt=0,
                quantity__lte=F("low_stock_threshold"),
            ).count(),
            "out_of_stock_count": Inventory.objects.filter(
                quantity=0
            ).count(),

            # Purchases
            "total_purchases": Purchase.objects.count(),
            "received_purchases": Purchase.objects.filter(
                status=Purchase.Status.RECEIVED
            ).count(),
            "purchase_total": get_purchase_total(),

            # Recent records
            "recent_orders": Order.objects.select_related(
                "customer"
            ).order_by("-created_at")[:5],

            "recent_categories": Category.objects.select_related(
                "created_by"
            ).order_by("-created_at")[:5],

            "recent_activities": AuditLog.objects.select_related(
                "user"
            ).exclude(
                app_label="dashboard"
            ).order_by("-created_at")[:8],
        })

    # -------------------------------------------------
    # INVENTORY MANAGER DASHBOARD
    # -------------------------------------------------
    elif is_inventory_manager:

        context.update({
            "total_categories": Category.objects.count(),
            "active_categories": Category.objects.filter(
                is_active=True
            ).count(),

            "total_products": Product.objects.count(),
            "active_products": Product.objects.filter(
                is_active=True
            ).count(),

            "total_inventory_items": Inventory.objects.count(),
            "total_stock_quantity": (
                Inventory.objects.aggregate(
                    total=Sum("quantity")
                )["total"] or 0
            ),

            "low_stock_count": Inventory.objects.filter(
                quantity__gt=0,
                quantity__lte=F("low_stock_threshold"),
            ).count(),

            "out_of_stock_count": Inventory.objects.filter(
                quantity=0
            ).count(),

            "total_suppliers": Supplier.objects.count(),
            "active_suppliers": Supplier.objects.filter(
                is_active=True
            ).count(),

            "total_purchases": Purchase.objects.count(),
            "draft_purchases": Purchase.objects.filter(
                status=Purchase.Status.DRAFT
            ).count(),
            "ordered_purchases": Purchase.objects.filter(
                status=Purchase.Status.ORDERED
            ).count(),
            "received_purchases": Purchase.objects.filter(
                status=Purchase.Status.RECEIVED
            ).count(),
            "purchase_total": get_purchase_total(),

            "recent_stock_transactions": (
                StockTransaction.objects.select_related(
                    "inventory__product",
                    "created_by",
                ).order_by("-created_at")[:8]
            ),

            "recent_purchases": Purchase.objects.select_related(
                "supplier",
                "created_by",
            ).order_by("-created_at")[:5],

            "recent_activities": AuditLog.objects.select_related(
                "user"
            ).filter(
                app_label__in=[
                    "categories",
                    "products",
                    "inventory",
                    "suppliers",
                    "purchases",
                ]
            ).exclude(
                app_label="dashboard"
            ).order_by("-created_at")[:8],
        })

    # -------------------------------------------------
    # ORDER MANAGER DASHBOARD
    # -------------------------------------------------
    elif is_order_manager:

        context.update({
            "total_orders": Order.objects.count(),

            "pending_orders": Order.objects.filter(
                status=Order.Status.PENDING
            ).count(),

            "confirmed_orders": Order.objects.filter(
                status=Order.Status.CONFIRMED
            ).count(),

            "processing_orders": Order.objects.filter(
                status=Order.Status.PROCESSING
            ).count(),

            "shipped_orders": Order.objects.filter(
                status=Order.Status.SHIPPED
            ).count(),

            "delivered_orders": Order.objects.filter(
                status=Order.Status.DELIVERED
            ).count(),

            "cancelled_orders": Order.objects.filter(
                status=Order.Status.CANCELLED
            ).count(),

            "total_order_value": (
                Order.objects.exclude(
                    status=Order.Status.CANCELLED
                ).aggregate(
                    total=Sum("total_amount")
                )["total"] or Decimal("0.00")
            ),

            "unpaid_orders": Order.objects.filter(
                payment_status=Order.PaymentStatus.UNPAID
            ).count(),

            "paid_orders": Order.objects.filter(
                payment_status=Order.PaymentStatus.PAID
            ).count(),

            "recent_orders": Order.objects.select_related(
                "customer"
            ).order_by("-created_at")[:10],

            "recent_activities": AuditLog.objects.select_related(
                "user"
            ).filter(
                app_label="orders"
            ).exclude(
                app_label="dashboard"
            ).order_by("-created_at")[:8],
        })

    # -------------------------------------------------
    # CUSTOMER DASHBOARD: ONLY OWN DATA
    # -------------------------------------------------
    elif is_customer:

        customer_orders = Order.objects.filter(
            customer=user
        )

        context.update({
            "my_total_orders": customer_orders.count(),

            "my_pending_orders": customer_orders.filter(
                status=Order.Status.PENDING
            ).count(),

            "my_processing_orders": customer_orders.filter(
                status__in=[
                    Order.Status.CONFIRMED,
                    Order.Status.PROCESSING,
                    Order.Status.SHIPPED,
                ]
            ).count(),

            "my_delivered_orders": customer_orders.filter(
                status=Order.Status.DELIVERED
            ).count(),

            "my_cancelled_orders": customer_orders.filter(
                status=Order.Status.CANCELLED
            ).count(),

            "my_total_spending": (
                customer_orders.filter(
                    payment_status=Order.PaymentStatus.PAID
                ).aggregate(
                    total=Sum("total_amount")
                )["total"] or Decimal("0.00")
            ),

            "my_recent_orders": customer_orders.order_by(
                "-created_at"
            )[:8],

            "my_recent_activities": AuditLog.objects.filter(
                user=user
            ).exclude(
                app_label="dashboard"
            ).order_by("-created_at")[:8],
        })

    return render(
        request,
        "dashboard/dashboard.html",
        context,
    )

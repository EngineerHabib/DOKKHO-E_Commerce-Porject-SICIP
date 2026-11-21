
import csv

from datetime import timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import (
    Sum,
    Count,
    F,
    Q,
    DecimalField,
    ExpressionWrapper,
)
from django.db.models.functions import TruncDate
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone

from orders.models import Order, OrderItem
from products.models import Product
from inventory.models import Inventory, StockTransaction
from purchases.models import Purchase

from .forms import DateRangeForm


# --------------------------------------------------
# REPORT PERMISSION
# --------------------------------------------------

def report_manager_required(view_func):

    from functools import wraps

    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):

        allowed_roles = ["super_admin", "admin"]

        if (
            request.user.is_superuser
            or getattr(request.user, "role", None) in allowed_roles
        ):
            return view_func(request, *args, **kwargs)

        raise PermissionDenied(
            "You do not have permission to access reports."
        )

    return wrapper


# --------------------------------------------------
# DATE FILTER
# --------------------------------------------------

def get_report_dates(request):

    today = timezone.localdate()

    default_start = today - timedelta(days=29)

    form = DateRangeForm(
        request.GET or None,
        initial={
            "start_date": default_start,
            "end_date": today,
        }
    )

    if request.GET:

        if form.is_valid():
            start_date = (
                form.cleaned_data.get("start_date")
                or default_start
            )

            end_date = (
                form.cleaned_data.get("end_date")
                or today
            )

            return form, start_date, end_date

        return form, default_start, today

    return form, default_start, today


# --------------------------------------------------
# REPORT DASHBOARD
# --------------------------------------------------

@report_manager_required
def report_dashboard(request):

    form, start_date, end_date = get_report_dates(request)

    # ----------------------------------------------
    # ORDER REPORT
    # ----------------------------------------------

    orders = Order.objects.filter(
        created_at__date__gte=start_date,
        created_at__date__lte=end_date,
    )

    total_orders = orders.count()

    cancelled_orders = orders.filter(
        status=Order.Status.CANCELLED
    ).count()

    sales_orders = orders.exclude(
        status=Order.Status.CANCELLED
    )

    sales_summary = sales_orders.aggregate(
        total_sales=Sum("total_amount"),
        paid_amount=Sum(
            "total_amount",
            filter=Q(payment_status=Order.PaymentStatus.PAID)
        ),
        unpaid_amount=Sum(
            "total_amount",
            filter=Q(payment_status=Order.PaymentStatus.UNPAID)
        ),
        refunded_amount=Sum(
            "total_amount",
            filter=Q(payment_status=Order.PaymentStatus.REFUNDED)
        ),
    )

    total_sales = sales_summary["total_sales"] or Decimal("0.00")
    paid_amount = sales_summary["paid_amount"] or Decimal("0.00")
    unpaid_amount = sales_summary["unpaid_amount"] or Decimal("0.00")
    refunded_amount = sales_summary["refunded_amount"] or Decimal("0.00")

    order_statuses = []

    for value, label in Order.Status.choices:

        order_statuses.append({
            "label": label,
            "count": orders.filter(status=value).count(),
        })

    # ----------------------------------------------
    # BEST SELLING PRODUCTS
    # ----------------------------------------------

    top_products = (
        OrderItem.objects.filter(
            order__created_at__date__gte=start_date,
            order__created_at__date__lte=end_date,
        )
        .exclude(
            order__status=Order.Status.CANCELLED
        )
        .values(
            "product_name",
            "product_sku",
        )
        .annotate(
            total_quantity=Sum("quantity"),
            total_revenue=Sum("line_total"),
        )
        .order_by("-total_quantity")[:10]
    )

    # ----------------------------------------------
    # PRODUCT REPORT
    # ----------------------------------------------

    total_products = Product.objects.count()

    active_products = Product.objects.filter(
        is_active=True
    ).count()

    inactive_products = Product.objects.filter(
        is_active=False
    ).count()

    # ----------------------------------------------
    # INVENTORY REPORT
    # ----------------------------------------------

    inventory_items = Inventory.objects.select_related(
        "product"
    )

    inventory_summary = inventory_items.aggregate(
        total_stock=Sum("quantity"),
        total_inventory_products=Count("id"),
    )

    total_stock = inventory_summary["total_stock"] or 0

    total_inventory_products = (
        inventory_summary["total_inventory_products"] or 0
    )

    low_stock_items = inventory_items.filter(
        quantity__gt=0,
        quantity__lte=F("low_stock_threshold")
    )

    out_of_stock_items = inventory_items.filter(
        quantity=0
    )

    low_stock_count = low_stock_items.count()
    out_of_stock_count = out_of_stock_items.count()

    # ----------------------------------------------
    # STOCK TRANSACTION REPORT
    # ----------------------------------------------

    transactions = StockTransaction.objects.filter(
        created_at__date__gte=start_date,
        created_at__date__lte=end_date,
    )

    stock_in = transactions.filter(
        transaction_type=StockTransaction.TransactionType.STOCK_IN
    ).aggregate(
        total=Sum("quantity")
    )["total"] or 0

    stock_out = transactions.filter(
        transaction_type=StockTransaction.TransactionType.STOCK_OUT
    ).aggregate(
        total=Sum("quantity")
    )["total"] or 0

    stock_adjustments = transactions.filter(
        transaction_type=StockTransaction.TransactionType.ADJUSTMENT
    ).count()

    recent_transactions = transactions.select_related(
        "inventory__product",
        "created_by"
    )[:10]

    # ----------------------------------------------
    # PURCHASE REPORT
    # ----------------------------------------------

    purchase_items = ExpressionWrapper(
        F("items__quantity") * F("items__unit_cost"),
        output_field=DecimalField(
            max_digits=20,
            decimal_places=2
        )
    )

    purchases = (
        Purchase.objects.filter(
            status=Purchase.Status.RECEIVED,
            received_at__date__gte=start_date,
            received_at__date__lte=end_date,
        )
        .select_related("supplier")
        .annotate(
            calculated_total=Sum(purchase_items)
        )
        .order_by("-received_at")
    )

    purchase_summary = purchases.aggregate(
        total_purchase_cost=Sum("calculated_total"),
        total_received_purchases=Count("id"),
    )

    total_purchase_cost = (
        purchase_summary["total_purchase_cost"]
        or Decimal("0.00")
    )

    total_received_purchases = (
        purchase_summary["total_received_purchases"]
        or 0
    )

    # ----------------------------------------------
    # SALES CHART DATA
    # ----------------------------------------------

    daily_sales = (
        sales_orders
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(total=Sum("total_amount"))
        .order_by("day")
    )

    sales_chart_labels = [
        item["day"].strftime("%d %b")
        for item in daily_sales
    ]

    sales_chart_values = [
        float(item["total"] or 0)
        for item in daily_sales
    ]

    # ----------------------------------------------
    # CONTEXT
    # ----------------------------------------------

    context = {
        "form": form,
        "start_date": start_date,
        "end_date": end_date,

        # Orders and Sales
        "total_orders": total_orders,
        "cancelled_orders": cancelled_orders,
        "total_sales": total_sales,
        "paid_amount": paid_amount,
        "unpaid_amount": unpaid_amount,
        "refunded_amount": refunded_amount,
        "order_statuses": order_statuses,
        "top_products": top_products,

        # Products
        "total_products": total_products,
        "active_products": active_products,
        "inactive_products": inactive_products,

        # Inventory
        "total_stock": total_stock,
        "total_inventory_products": total_inventory_products,
        "low_stock_count": low_stock_count,
        "out_of_stock_count": out_of_stock_count,
        "low_stock_items": low_stock_items[:10],
        "out_of_stock_items": out_of_stock_items[:10],

        # Stock Transactions
        "stock_in": stock_in,
        "stock_out": stock_out,
        "stock_adjustments": stock_adjustments,
        "recent_transactions": recent_transactions,

        # Purchases
        "total_purchase_cost": total_purchase_cost,
        "total_received_purchases": total_received_purchases,
        "purchases": purchases[:10],

        # Chart
        "sales_chart_labels": sales_chart_labels,
        "sales_chart_values": sales_chart_values,
    }

    return render(
        request,
        "reports/report_dashboard.html",
        context
    )


# --------------------------------------------------
# ORDER CSV EXPORT
# --------------------------------------------------

@report_manager_required
def export_orders_csv(request):

    form, start_date, end_date = get_report_dates(request)

    if not form.is_valid():
        messages.error(
            request,
            "Please select a valid date range."
        )

        return render(
            request,
            "reports/report_dashboard.html",
            {
                "form": form,
                "start_date": start_date,
                "end_date": end_date,
            }
        )

    orders = Order.objects.filter(
        created_at__date__gte=start_date,
        created_at__date__lte=end_date,
    ).select_related(
        "customer"
    ).order_by("-created_at")

    response = HttpResponse(
        content_type="text/csv; charset=utf-8"
    )

    response["Content-Disposition"] = (
        f'attachment; filename="smartcommerce_orders_'
        f'{start_date}_{end_date}.csv"'
    )

    response.write("\ufeff")

    writer = csv.writer(response)

    writer.writerow([
        "Order Number",
        "Customer",
        "Email",
        "Phone",
        "Order Status",
        "Payment Method",
        "Payment Status",
        "Subtotal",
        "Delivery Charge",
        "Total Amount",
        "Order Date",
    ])

    for order in orders:

        writer.writerow([
            order.order_number,
            order.customer_name,
            order.email,
            order.phone,
            order.get_status_display(),
            order.get_payment_method_display(),
            order.get_payment_status_display(),
            order.subtotal,
            order.delivery_charge,
            order.total_amount,
            timezone.localtime(order.created_at).strftime(
                "%Y-%m-%d %H:%M"
            ),
        ])

    return response

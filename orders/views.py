
from functools import wraps
from decimal import Decimal
import logging

from django.shortcuts import (
    render,
    redirect,
    get_object_or_404,
)
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q
from django.views.decorators.http import require_POST

from products.models import Product
from inventory.models import Inventory, StockTransaction

from .models import Order, OrderItem
from .forms import OrderCreateForm, CartCheckoutForm

from cart.models import Cart, CartItem


logger = logging.getLogger(__name__)


# =====================================================
# CONFIGURATION
# =====================================================

MANAGER_ROLES = [
    "super_admin",
    "admin",
    "order_manager",
]

DELIVERY_CHARGE = Decimal("80.00")


# =====================================================
# ORDER STATUS WORKFLOW
# =====================================================

ALLOWED_STATUS_TRANSITIONS = {
    Order.Status.PENDING: [
        Order.Status.CONFIRMED,
        Order.Status.CANCELLED,
    ],

    Order.Status.CONFIRMED: [
        Order.Status.PROCESSING,
    ],

    Order.Status.PROCESSING: [
        Order.Status.SHIPPED,
    ],

    Order.Status.SHIPPED: [
        Order.Status.DELIVERED,
    ],

    Order.Status.DELIVERED: [],

    Order.Status.CANCELLED: [],
}


def get_manager_status_choices(order):

    allowed_statuses = ALLOWED_STATUS_TRANSITIONS.get(
        order.status,
        [],
    )

    available_statuses = [
        order.status,
        *allowed_statuses,
    ]

    return [
        (value, label)
        for value, label in Order.Status.choices
        if value in available_statuses
    ]


# =====================================================
# ORDER MANAGER PERMISSION
# =====================================================

def order_manager_required(view_func):

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):

        if (
            request.user.is_superuser
            or getattr(request.user, "role", None) in MANAGER_ROLES
        ):
            return view_func(request, *args, **kwargs)

        raise PermissionDenied(
            "You do not have permission to manage orders."
        )

    return login_required(wrapper)


# =====================================================
# RESTORE ORDER STOCK
# =====================================================

def restore_order_stock(order, user):

    items = list(
        order.items.select_related("product")
    )

    for item in items:

        if not item.product_id:
            continue

        inventory = (
            Inventory.objects
            .select_for_update()
            .filter(product_id=item.product_id)
            .first()
        )

        if inventory is None:

            logger.warning(
                "Inventory not found for product ID %s "
                "while cancelling order %s.",
                item.product_id,
                order.order_number,
            )

            continue

        previous_quantity = inventory.quantity

        new_quantity = (
            previous_quantity + item.quantity
        )

        inventory.quantity = new_quantity

        inventory.save(
            update_fields=[
                "quantity",
                "updated_at",
            ]
        )

        StockTransaction.objects.create(
            inventory=inventory,

            transaction_type=(
                StockTransaction.TransactionType.STOCK_IN
            ),

            quantity=item.quantity,

            previous_quantity=previous_quantity,

            new_quantity=new_quantity,

            note=f"Cancelled Order #{order.order_number}",

            created_by=user,
        )


# =====================================================
# CREATE ORDER / PRODUCT CHECKOUT
# =====================================================

@login_required
def order_create(request, slug):

    product = get_object_or_404(
        Product,
        slug=slug,
        is_active=True,
    )

    inventory = Inventory.objects.filter(
        product=product
    ).first()

    available_stock = (
        inventory.quantity if inventory else 0
    )

    initial_data = {
        "customer_name": (
            request.user.get_full_name()
            or request.user.username
        ),

        "email": request.user.email,

        "phone": request.user.phone,

        "shipping_address": request.user.address,

        "payment_method": Order.PaymentMethod.COD,
    }

    form = OrderCreateForm(
        request.POST or None,
        initial=initial_data,
    )

    if request.method == "POST" and form.is_valid():

        quantity = form.cleaned_data["quantity"]

        try:

            with transaction.atomic():

                locked_inventory = (
                    Inventory.objects
                    .select_for_update()
                    .get(product=product)
                )

                if quantity > locked_inventory.quantity:

                    available_stock = locked_inventory.quantity

                    form.add_error(
                        "quantity",
                        f"Only {available_stock} units are available.",
                    )

                else:

                    unit_price = product.discount_price

                    subtotal = unit_price * quantity

                    total_amount = (
                        subtotal + DELIVERY_CHARGE
                    )

                    order = form.save(commit=False)

                    order.customer = request.user
                    order.subtotal = subtotal
                    order.delivery_charge = DELIVERY_CHARGE
                    order.total_amount = total_amount

                    order.save()

                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        product_name=product.name,
                        product_sku=product.sku,
                        quantity=quantity,
                        unit_price=unit_price,
                        line_total=subtotal,
                    )

                    # Reduce inventory

                    previous_quantity = locked_inventory.quantity

                    new_quantity = (
                        previous_quantity - quantity
                    )

                    locked_inventory.quantity = new_quantity

                    locked_inventory.save(
                        update_fields=[
                            "quantity",
                            "updated_at",
                        ]
                    )

                    # Record stock transaction

                    StockTransaction.objects.create(
                        inventory=locked_inventory,

                        transaction_type=(
                            StockTransaction.TransactionType.STOCK_OUT
                        ),

                        quantity=quantity,

                        previous_quantity=previous_quantity,

                        new_quantity=new_quantity,

                        note=f"Order #{order.order_number}",

                        created_by=request.user,
                    )

                    messages.success(
                        request,
                        "Your order has been placed successfully.",
                    )

                    return redirect(
                        "orders:order_success",
                        order_number=order.order_number,
                    )

        except Inventory.DoesNotExist:

            form.add_error(
                "quantity",
                "Inventory record was not found.",
            )

    context = {
        "form": form,
        "product": product,
        "available_stock": available_stock,
        "delivery_charge": DELIVERY_CHARGE,

        "title": "Complete Your Order",

        "description": (
            "Enter your delivery information to confirm your order."
        ),

        "button_text": "Confirm Order",
        "button_icon": "bi bi-check-circle",

        "form_width": "col-lg-10 col-xl-9",

        "cancel_url": reverse("products:product_list"),
    }

    return render(
        request,
        "orders/order_form.html",
        context,
    )


# =====================================================
# ORDER SUCCESS
# =====================================================

@login_required
def order_success(request, order_number):

    order = get_object_or_404(
        Order,
        order_number=order_number,
        customer=request.user,
    )

    return render(
        request,
        "orders/order_success.html",
        {
            "order": order,
            "title": "Order Confirmed",
        },
    )


# =====================================================
# CUSTOMER: MY ORDERS
# =====================================================

@login_required
def my_orders(request):

    orders = (
        Order.objects
        .filter(customer=request.user)
        .prefetch_related("items")
        .order_by("-created_at")
    )

    context = {
        "orders": orders,
        "title": "My Orders",
    }

    return render(
        request,
        "orders/my_orders.html",
        context,
    )


# =====================================================
# CUSTOMER: ORDER DETAILS
# =====================================================

@login_required
def order_detail(request, order_number):

    order = get_object_or_404(
        Order.objects.prefetch_related("items"),
        order_number=order_number,
        customer=request.user,
    )

    return render(
        request,
        "orders/order_detail.html",
        {
            "order": order,
            "title": "Order Details",
        },
    )


# =====================================================
# CUSTOMER: CANCEL OWN ORDER
# =====================================================

@login_required
@require_POST
def order_cancel(request, order_number):

    with transaction.atomic():

        order = get_object_or_404(
            Order.objects.select_for_update(),
            order_number=order_number,
            customer=request.user,
        )

        if order.status != Order.Status.PENDING:

            messages.error(
                request,
                "Only pending orders can be cancelled.",
            )

            return redirect(
                "orders:order_detail",
                order_number=order.order_number,
            )

        restore_order_stock(
            order,
            request.user,
        )

        order.status = Order.Status.CANCELLED

        order.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

    messages.success(
        request,
        "Your order has been cancelled successfully.",
    )

    return redirect(
        "orders:order_detail",
        order_number=order.order_number,
    )


# =====================================================
# MANAGER: ALL ORDERS
# =====================================================

@order_manager_required
def manage_orders(request):

    orders = (
        Order.objects
        .select_related("customer")
        .prefetch_related("items")
    )

    search = request.GET.get(
        "search",
        "",
    ).strip()

    status = request.GET.get(
        "status",
        "",
    ).strip()

    if search:

        orders = orders.filter(
            Q(order_number__icontains=search)
            | Q(customer_name__icontains=search)
            | Q(phone__icontains=search)
        )

    valid_statuses = Order.Status.values

    if status in valid_statuses:

        orders = orders.filter(
            status=status
        )

    context = {
        "orders": orders,
        "search": search,
        "status": status,
        "status_choices": Order.Status.choices,
        "title": "Manage Orders",
    }

    return render(
        request,
        "orders/manage_orders.html",
        context,
    )


# =====================================================
# MANAGER: ORDER DETAILS
# =====================================================

@order_manager_required
def manage_order_detail(request, order_number):

    order = get_object_or_404(
        Order.objects
        .select_related("customer")
        .prefetch_related("items"),
        order_number=order_number,
    )

    context = {
        "order": order,

        # Only show valid next status options
        "status_choices": get_manager_status_choices(order),

        "title": "Manage Order",
    }

    return render(
        request,
        "orders/manage_order_detail.html",
        context,
    )


# =====================================================
# MANAGER: UPDATE ORDER STATUS
# =====================================================

@order_manager_required
@require_POST
def update_order_status(request, order_number):

    new_status = request.POST.get(
        "status",
        "",
    ).strip()

    if new_status not in Order.Status.values:

        messages.error(
            request,
            "Invalid order status.",
        )

        return redirect(
            "orders:manage_order_detail",
            order_number=order_number,
        )

    with transaction.atomic():

        order = get_object_or_404(
            Order.objects.select_for_update(),
            order_number=order_number,
        )

        current_status = order.status

        # Already cancelled

        if current_status == Order.Status.CANCELLED:

            messages.error(
                request,
                "Cancelled orders cannot be updated.",
            )

        # Already delivered

        elif current_status == Order.Status.DELIVERED:

            messages.error(
                request,
                "Delivered orders cannot be updated.",
            )

        # Same status selected

        elif new_status == current_status:

            messages.warning(
                request,
                "Order is already in this status.",
            )

        # Cancellation

        elif new_status == Order.Status.CANCELLED:

            if current_status != Order.Status.PENDING:

                messages.error(
                    request,
                    "Only pending orders can be cancelled.",
                )

            else:

                restore_order_stock(
                    order,
                    request.user,
                )

                order.status = Order.Status.CANCELLED

                order.save(
                    update_fields=[
                        "status",
                        "updated_at",
                    ]
                )

                messages.success(
                    request,
                    "Order cancelled and stock restored successfully.",
                )

        # Normal status transition

        else:

            allowed_statuses = ALLOWED_STATUS_TRANSITIONS.get(
                current_status,
                [],
            )

            if new_status not in allowed_statuses:

                messages.error(
                    request,
                    "Invalid status transition. "
                    "Please follow the order workflow.",
                )

            else:

                order.status = new_status

                # COD payment is considered paid on delivery
                if new_status == Order.Status.DELIVERED:

                    order.payment_status = (
                        Order.PaymentStatus.PAID
                    )

                order.save(
                    update_fields=[
                        "status",
                        "payment_status",
                        "updated_at",
                    ]
                )

                messages.success(
                    request,
                    f"Order status updated to {order.get_status_display()}.",
                )

    return redirect(
        "orders:manage_order_detail",
        order_number=order_number,
    )


# =====================================================
# CUSTOMER: CART CHECKOUT
# =====================================================

@login_required
def cart_checkout(request):

    cart = get_object_or_404(
        Cart.objects.prefetch_related(
            "items__product"
        ),
        user=request.user,
    )

    cart_items = list(
        cart.items.select_related("product").all()
    )

    if not cart_items:

        messages.error(
            request,
            "Your cart is empty.",
        )

        return redirect("cart:cart_detail")

    delivery_charge = DELIVERY_CHARGE

    # Initial form data

    initial_data = {
        "customer_name": (
            request.user.get_full_name()
            or request.user.username
        ),

        "email": request.user.email,

        "phone": request.user.phone,

        "shipping_address": request.user.address,
    }

    form = CartCheckoutForm(
        request.POST or None,
        initial=initial_data,
    )

    # Display totals

    subtotal = sum(
        (
            item.product.discount_price * item.quantity
            for item in cart_items
        ),
        Decimal("0.00"),
    )

    total_amount = subtotal + delivery_charge

    # Process checkout

    if request.method == "POST":

        if form.is_valid():

            try:

                with transaction.atomic():

                    # Lock cart

                    locked_cart = (
                        Cart.objects
                        .select_for_update()
                        .get(user=request.user)
                    )

                    # Lock cart items

                    locked_items = list(
                        CartItem.objects
                        .select_for_update()
                        .filter(cart=locked_cart)
                        .select_related("product")
                        .order_by("product_id")
                    )

                    if not locked_items:

                        raise ValueError(
                            "Your cart is empty."
                        )

                    inventory_map = {}

                    # Validate products and inventory

                    for item in locked_items:

                        product = item.product

                        if not product.is_active:

                            raise ValueError(
                                f"{product.name} is unavailable."
                            )

                        if item.quantity <= 0:

                            raise ValueError(
                                f"Invalid quantity for {product.name}."
                            )

                        if product.discount_price is None:

                            raise ValueError(
                                f"Price is not available for {product.name}."
                            )

                        if product.discount_price < 0:

                            raise ValueError(
                                f"Invalid price for {product.name}."
                            )

                        inventory = (
                            Inventory.objects
                            .select_for_update()
                            .filter(product_id=product.id)
                            .first()
                        )

                        if inventory is None:

                            raise ValueError(
                                f"Inventory not found for {product.name}."
                            )

                        if item.quantity > inventory.quantity:

                            raise ValueError(
                                f"Only {inventory.quantity} units of "
                                f"{product.name} are available."
                            )

                        inventory_map[product.id] = inventory

                    # Calculate final amount

                    subtotal = sum(
                        (
                            item.product.discount_price * item.quantity
                            for item in locked_items
                        ),
                        Decimal("0.00"),
                    )

                    total_amount = (
                        subtotal + delivery_charge
                    )

                    # Create order

                    order = Order.objects.create(

                        customer=request.user,

                        customer_name=form.cleaned_data[
                            "customer_name"
                        ],

                        email=form.cleaned_data[
                            "email"
                        ],

                        phone=form.cleaned_data[
                            "phone"
                        ],

                        shipping_address=form.cleaned_data[
                            "shipping_address"
                        ],

                        note=form.cleaned_data[
                            "note"
                        ],

                        payment_method=Order.PaymentMethod.COD,

                        subtotal=subtotal,

                        delivery_charge=delivery_charge,

                        total_amount=total_amount,
                    )

                    # Create order items and reduce stock

                    for item in locked_items:

                        product = item.product

                        inventory = inventory_map[
                            product.id
                        ]

                        unit_price = product.discount_price

                        line_total = (
                            unit_price * item.quantity
                        )

                        OrderItem.objects.create(

                            order=order,

                            product=product,

                            product_name=product.name,

                            product_sku=product.sku,

                            quantity=item.quantity,

                            unit_price=unit_price,

                            line_total=line_total,
                        )

                        # Reduce inventory

                        previous_quantity = inventory.quantity

                        new_quantity = (
                            previous_quantity - item.quantity
                        )

                        inventory.quantity = new_quantity

                        inventory.save(
                            update_fields=[
                                "quantity",
                                "updated_at",
                            ]
                        )

                        # Record stock transaction

                        StockTransaction.objects.create(

                            inventory=inventory,

                            transaction_type=(
                                StockTransaction.TransactionType.STOCK_OUT
                            ),

                            quantity=item.quantity,

                            previous_quantity=previous_quantity,

                            new_quantity=new_quantity,

                            note=f"Order #{order.order_number}",

                            created_by=request.user,
                        )

                    # Clear cart

                    CartItem.objects.filter(
                        cart=locked_cart
                    ).delete()

                messages.success(
                    request,
                    "Your order has been placed successfully.",
                )

                return redirect(
                    "orders:order_success",
                    order_number=order.order_number,
                )

            except ValueError as error:

                messages.error(
                    request,
                    str(error),
                )

            except Exception:

                logger.exception(
                    "Cart checkout failed for user ID %s",
                    request.user.id,
                )

                messages.error(
                    request,
                    "Unable to place your order. "
                    "Please check the server error.",
                )

        else:

            messages.error(
                request,
                "Please correct the checkout form errors.",
            )

    # Refresh cart data

    cart.refresh_from_db()

    cart_items = list(
        cart.items.select_related("product").all()
    )

    subtotal = sum(
        (
            item.product.discount_price * item.quantity
            for item in cart_items
        ),
        Decimal("0.00"),
    )

    total_amount = subtotal + delivery_charge

    context = {
        "form": form,
        "cart": cart,
        "cart_items": cart_items,
        "delivery_charge": delivery_charge,
        "subtotal": subtotal,
        "total_amount": total_amount,
        "title": "Checkout",
    }

    return render(
        request,
        "orders/cart_checkout.html",
        context,
    )


@order_manager_required
@require_POST
def reopen_cancelled_order(request, order_number):

    try:
        with transaction.atomic():

            # Lock the order
            order = get_object_or_404(
                Order.objects.select_for_update(),
                order_number=order_number
            )

            # Only cancelled orders can be reopened
            if order.status != Order.Status.CANCELLED:
                raise ValueError(
                    "Only cancelled orders can be reopened."
                )

            order_items = list(
                order.items.select_related("product")
            )

            if not order_items:
                raise ValueError("This order has no items.")

            inventory_records = []

            # First validate ALL products and stock
            for item in order_items:

                if item.product_id is None:
                    raise ValueError(
                        f"{item.product_name} is no longer available."
                    )

                inventory = Inventory.objects.select_for_update().filter(
                    product_id=item.product_id
                ).first()

                if inventory is None:
                    raise ValueError(
                        f"Inventory not found for {item.product_name}."
                    )

                if inventory.quantity < item.quantity:
                    raise ValueError(
                        f"Insufficient stock for {item.product_name}. "
                        f"Available: {inventory.quantity}, "
                        f"Required: {item.quantity}."
                    )

                inventory_records.append((item, inventory))

            # Deduct stock only after all products pass validation
            for item, inventory in inventory_records:

                previous_quantity = inventory.quantity
                inventory.quantity -= item.quantity

                inventory.save(update_fields=[
                    "quantity",
                    "updated_at"
                ])

                StockTransaction.objects.create(
                    inventory=inventory,
                    transaction_type=(
                        StockTransaction.TransactionType.STOCK_OUT
                    ),
                    quantity=item.quantity,
                    previous_quantity=previous_quantity,
                    new_quantity=inventory.quantity,
                    note=f"Stock deducted after reopening order {order.order_number}",
                    created_by=request.user
                )

            # Reopen the order
            order.status = Order.Status.PENDING
            order.save(update_fields=["status"])

        messages.success(
            request,
            "Order reopened successfully. You can now confirm this order."
        )

    except ValueError as e:
        messages.error(request, str(e))

    return redirect(
        "orders:manage_order_detail",
        order_number=order_number
    )
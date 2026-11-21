
from django.shortcuts import (
    render,
    redirect,
    get_object_or_404,
)
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.views.decorators.http import require_POST

from products.models import Product
from inventory.models import Inventory

from .models import Cart, CartItem
from .forms import CartItemForm


def get_user_cart(user):

    cart, created = Cart.objects.get_or_create(
        user=user
    )

    return cart


# =====================================================
# CART DETAIL
# =====================================================

@login_required
def cart_detail(request):

    cart = get_user_cart(request.user)

    cart_items = (
        cart.items
        .select_related("product")
        .all()
    )

    item_data = []

    for item in cart_items:

        inventory = Inventory.objects.filter(
            product=item.product
        ).first()

        available_stock = (
            inventory.quantity if inventory else 0
        )

        item_data.append({
            "item": item,
            "form": CartItemForm(instance=item),
            "available_stock": available_stock,
            "is_available": (
                item.product.is_active
                and available_stock >= item.quantity
            ),
        })

    context = {
        "cart": cart,
        "item_data": item_data,
        "title": "Shopping Cart",
    }

    return render(
        request,
        "cart/cart_detail.html",
        context,
    )


# =====================================================
# ADD TO CART
# =====================================================

@login_required
@require_POST
def add_to_cart(request, slug):

    product = get_object_or_404(
        Product,
        slug=slug,
        is_active=True,
    )

    form = CartItemForm(request.POST)

    if not form.is_valid():

        messages.error(
            request,
            "Please enter a valid quantity.",
        )

        return redirect(
            "products:product_detail",
            slug=product.slug,
        )

    quantity = form.cleaned_data["quantity"]

    inventory = Inventory.objects.filter(
        product=product
    ).first()

    if not inventory or inventory.quantity < 1:

        messages.error(
            request,
            "This product is currently out of stock.",
        )

        return redirect(
            "products:product_detail",
            slug=product.slug,
        )

    cart = get_user_cart(request.user)

    with transaction.atomic():

        locked_inventory = (
            Inventory.objects
            .select_for_update()
            .filter(product=product)
            .first()
        )

        if not locked_inventory:

            messages.error(
                request,
                "Inventory record was not found.",
            )

            return redirect("cart:cart_detail")

        cart_item = (
            CartItem.objects
            .select_for_update()
            .filter(
                cart=cart,
                product=product,
            )
            .first()
        )

        existing_quantity = (
            cart_item.quantity if cart_item else 0
        )

        new_quantity = existing_quantity + quantity

        if new_quantity > locked_inventory.quantity:

            messages.error(
                request,
                f"Only {locked_inventory.quantity} units are available.",
            )

            return redirect("cart:cart_detail")

        if cart_item:

            cart_item.quantity = new_quantity

            cart_item.save(
                update_fields=[
                    "quantity",
                    "updated_at",
                ]
            )

        else:

            CartItem.objects.create(
                cart=cart,
                product=product,
                quantity=quantity,
            )

    messages.success(
        request,
        f"{product.name} added to your cart.",
    )

    return redirect("cart:cart_detail")


# =====================================================
# UPDATE CART ITEM
# =====================================================

@login_required
@require_POST
def update_cart_item(request, item_id):

    cart = get_user_cart(request.user)

    cart_item = get_object_or_404(
        CartItem,
        pk=item_id,
        cart=cart,
    )

    form = CartItemForm(
        request.POST,
        instance=cart_item,
    )

    if not form.is_valid():

        messages.error(
            request,
            "Please enter a valid quantity.",
        )

        return redirect("cart:cart_detail")

    quantity = form.cleaned_data["quantity"]

    with transaction.atomic():

        inventory = (
            Inventory.objects
            .select_for_update()
            .filter(product=cart_item.product)
            .first()
        )

        if not inventory:

            messages.error(
                request,
                "Inventory record was not found.",
            )

            return redirect("cart:cart_detail")

        if quantity > inventory.quantity:

            messages.error(
                request,
                f"Only {inventory.quantity} units are available.",
            )

            return redirect("cart:cart_detail")

        cart_item.quantity = quantity

        cart_item.save(
            update_fields=[
                "quantity",
                "updated_at",
            ]
        )

    messages.success(
        request,
        "Cart quantity updated successfully.",
    )

    return redirect("cart:cart_detail")


# =====================================================
# REMOVE CART ITEM
# =====================================================

@login_required
@require_POST
def remove_cart_item(request, item_id):

    cart = get_user_cart(request.user)

    cart_item = get_object_or_404(
        CartItem,
        pk=item_id,
        cart=cart,
    )

    product_name = cart_item.product.name

    cart_item.delete()

    messages.success(
        request,
        f"{product_name} removed from your cart.",
    )

    return redirect("cart:cart_detail")


# =====================================================
# CLEAR CART
# =====================================================

@login_required
@require_POST
def clear_cart(request):

    cart = get_user_cart(request.user)

    cart.items.all().delete()

    messages.success(
        request,
        "Your cart has been cleared.",
    )

    return redirect("cart:cart_detail")

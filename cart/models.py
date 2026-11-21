
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Sum, F

from products.models import Product


class Cart(models.Model):

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cart",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Cart - {self.user.username}"

    @property
    def total_items(self):
        return self.items.aggregate(
            total=Sum("quantity")
        )["total"] or 0

    @property
    def subtotal(self):
        return sum(
            (
                item.line_total
                for item in self.items.select_related("product")
            ),
            Decimal("0.00"),
        )

    @property
    def is_empty(self):
        return not self.items.exists()


class CartItem(models.Model):

    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name="items",
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="cart_items",
    )

    quantity = models.PositiveIntegerField(default=1)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

        constraints = [
            models.UniqueConstraint(
                fields=["cart", "product"],
                name="unique_product_per_cart",
            )
        ]

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"

    @property
    def unit_price(self):
        return self.product.discount_price

    @property
    def line_total(self):
        return self.unit_price * self.quantity

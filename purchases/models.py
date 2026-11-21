
import uuid

from decimal import Decimal

from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator

from suppliers.models import Supplier
from products.models import Product


class Purchase(models.Model):

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        ORDERED = "ORDERED", "Ordered"
        RECEIVED = "RECEIVED", "Received"
        CANCELLED = "CANCELLED", "Cancelled"

    purchase_number = models.CharField(
        max_length=30,
        unique=True,
        blank=True
    )

    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        related_name="purchases"
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )

    purchase_date = models.DateField(
        auto_now_add=True
    )

    expected_delivery_date = models.DateField(
        null=True,
        blank=True
    )

    received_at = models.DateTimeField(
        null=True,
        blank=True
    )

    notes = models.TextField(
        blank=True
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_purchases"
    )

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_purchases"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Purchase"
        verbose_name_plural = "Purchases"

    def save(self, *args, **kwargs):

        if not self.purchase_number:
            self.purchase_number = (
                f"PO-{uuid.uuid4().hex[:12].upper()}"
            )

        super().save(*args, **kwargs)

    @property
    def total_amount(self):

        return sum(
            (item.line_total for item in self.items.all()),
            Decimal("0.00")
        )

    @property
    def total_items(self):
        return self.items.count()

    @property
    def total_quantity(self):
        return sum(
            self.items.values_list("quantity", flat=True)
        )

    def __str__(self):
        return self.purchase_number


class PurchaseItem(models.Model):

    purchase = models.ForeignKey(
        Purchase,
        on_delete=models.CASCADE,
        related_name="items"
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="purchase_items"
    )

    quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)]
    )

    unit_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))]
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(
                fields=["purchase", "product"],
                name="unique_product_per_purchase"
            )
        ]
        verbose_name = "Purchase Item"
        verbose_name_plural = "Purchase Items"

    @property
    def line_total(self):
        return self.quantity * self.unit_cost

    def __str__(self):
        return f"{self.product.name} - {self.quantity}"

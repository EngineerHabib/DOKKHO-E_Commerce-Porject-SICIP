
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator

from products.models import Product


class Inventory(models.Model):

    product = models.OneToOneField(
        Product,
        on_delete=models.CASCADE,
        related_name="inventory"
    )

    quantity = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0)]
    )

    low_stock_threshold = models.PositiveIntegerField(
        default=5,
        help_text="Minimum stock quantity warning limit."
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        verbose_name = "Inventory"
        verbose_name_plural = "Inventories"

    @property
    def is_low_stock(self):
        return 0 < self.quantity <= self.low_stock_threshold

    @property
    def is_out_of_stock(self):
        return self.quantity == 0

    def __str__(self):
        return f"{self.product.name} - {self.quantity}"


class StockTransaction(models.Model):

    class TransactionType(models.TextChoices):
        STOCK_IN = "IN", "Stock In"
        STOCK_OUT = "OUT", "Stock Out"
        ADJUSTMENT = "ADJUSTMENT", "Adjustment"

    inventory = models.ForeignKey(
        Inventory,
        on_delete=models.CASCADE,
        related_name="transactions"
    )

    transaction_type = models.CharField(
        max_length=20,
        choices=TransactionType.choices
    )

    quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)]
    )

    previous_quantity = models.PositiveIntegerField()

    new_quantity = models.PositiveIntegerField()

    note = models.TextField(
        blank=True
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="stock_transactions"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Stock Transaction"
        verbose_name_plural = "Stock Transactions"

    def __str__(self):
        return (
            f"{self.inventory.product.name} - "
            f"{self.get_transaction_type_display()} - "
            f"{self.quantity}"
        )

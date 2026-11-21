
from decimal import Decimal

from django.db import models
from django.conf import settings
from django.utils.text import slugify
from django.core.validators import (
    MinValueValidator,
    MaxValueValidator,
)

from categories.models import Category


class Product(models.Model):

    # ==========================================
    # PRODUCT INFORMATION
    # ==========================================

    sku = models.CharField(
        max_length=50,
        unique=True
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="products"
    )

    name = models.CharField(
        max_length=200
    )

    slug = models.SlugField(
        max_length=220,
        unique=True,
        blank=True
    )

    description = models.TextField(
        blank=True
    )

    # ==========================================
    # PRODUCT PRICE
    # ==========================================

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0.01"))
        ]
    )

    discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[
            MinValueValidator(Decimal("0.00")),
            MaxValueValidator(Decimal("100.00"))
        ]
    )

    # ==========================================
    # PRODUCT IMAGE
    # ==========================================

    image = models.ImageField(
        upload_to="products/",
        blank=True,
        null=True
    )

    # ==========================================
    # PRODUCT STATUS
    # ==========================================

    is_active = models.BooleanField(
        default=True
    )

    # ==========================================
    # USER INFORMATION
    # ==========================================

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_products"
    )

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="updated_products"
    )

    # ==========================================
    # TIMESTAMPS
    # ==========================================

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    # ==========================================
    # MODEL SETTINGS
    # ==========================================

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Product"
        verbose_name_plural = "Products"

    # ==========================================
    # DISCOUNT CALCULATION
    # ==========================================

    @property
    def discount_amount(self):

        return (
            self.price * self.discount_percentage
        ) / Decimal("100")

    @property
    def discount_price(self):

        return self.price - self.discount_amount

    @property
    def has_discount(self):

        return self.discount_percentage > 0

    # ==========================================
    # PRODUCT SLUG GENERATION
    # ==========================================

    def save(self, *args, **kwargs):

        if not self.slug:

            base_slug = slugify(self.name)

            if not base_slug:
                base_slug = "product"

            unique_slug = base_slug
            counter = 1

            while Product.objects.filter(
                slug=unique_slug
            ).exclude(pk=self.pk).exists():

                counter += 1

                unique_slug = (
                    f"{base_slug}-{counter}"
                )

            self.slug = unique_slug

        super().save(*args, **kwargs)

    # ==========================================
    # STRING REPRESENTATION
    # ==========================================

    def __str__(self):

        return self.name

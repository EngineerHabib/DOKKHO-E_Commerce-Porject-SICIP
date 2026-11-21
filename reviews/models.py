
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator

from products.models import Product


class Review(models.Model):

    RATING_CHOICES = [
        (1, "1 Star"),
        (2, "2 Stars"),
        (3, "3 Stars"),
        (4, "4 Stars"),
        (5, "5 Stars"),
    ]

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="reviews"
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="product_reviews"
    )

    rating = models.PositiveSmallIntegerField(
        choices=RATING_CHOICES,
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5),
        ]
    )

    title = models.CharField(
        max_length=150
    )

    comment = models.TextField()

    is_approved = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ["-created_at"]

        verbose_name = "Product Review"
        verbose_name_plural = "Product Reviews"

        constraints = [
            models.UniqueConstraint(
                fields=["product", "user"],
                name="unique_user_product_review"
            )
        ]

    def __str__(self):
        return f"{self.product.name} - {self.user} - {self.rating} Stars"

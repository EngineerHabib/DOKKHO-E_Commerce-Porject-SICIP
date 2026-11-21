
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):

    class Role(models.TextChoices):
        SUPER_ADMIN = "super_admin", _("Super Admin")
        ADMIN = "admin", _("Admin")
        INVENTORY_MANAGER = "inventory_manager", _("Inventory Manager")
        ORDER_MANAGER = "order_manager", _("Order Manager")
        CUSTOMER = "customer", _("Customer")

    email = models.EmailField(
        unique=True,
        verbose_name="Email Address"
    )

    phone = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True
    )

    role = models.CharField(
        max_length=30,
        choices=Role.choices,
        default=Role.CUSTOMER
    )

    profile_image = models.ImageField(
        upload_to="profiles/",
        null=True,
        blank=True
    )

    address = models.TextField(
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.username

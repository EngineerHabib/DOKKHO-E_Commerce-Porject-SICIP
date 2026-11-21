
from django import forms
from django.db import models
from decimal import Decimal

from .models import Product
from categories.models import Category
from inventory.models import Inventory


class ProductForm(forms.ModelForm):

    quantity = forms.IntegerField(
        label="Available Quantity",
        required=False,
        min_value=0,
        initial=0,
        widget=forms.NumberInput(attrs={
            "class": "form-control",
            "placeholder": "Enter available quantity",
            "min": "0",
            "step": "1",
        })
    )

    class Meta:
        model = Product

        fields = [
            "sku",
            "category",
            "name",
            "description",
            "price",
            "discount_percentage",
            "image",
            "is_active",
            "quantity",
        ]

        widgets = {
            "sku": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter product SKU",
            }),

            "category": forms.Select(attrs={
                "class": "form-select",
            }),

            "name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter product name",
            }),

            "description": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Product description",
            }),

            "price": forms.NumberInput(attrs={
                "class": "form-control",
                "placeholder": "Enter regular price",
                "min": "0.01",
                "step": "0.01",
            }),

            "discount_percentage": forms.NumberInput(attrs={
                "class": "form-control",
                "placeholder": "Enter discount percentage",
                "min": "0",
                "max": "100",
                "step": "0.01",
            }),

            "image": forms.ClearableFileInput(attrs={
                "class": "form-control",
            }),

            "is_active": forms.CheckboxInput(attrs={
                "class": "form-check-input",
            }),
        }

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        categories = Category.objects.filter(
            is_active=True
        )

        if self.instance and self.instance.pk:

            categories = Category.objects.filter(
                models.Q(is_active=True)
                | models.Q(pk=self.instance.category_id)
            )

            try:
                inventory = self.instance.inventory
                self.fields["quantity"].initial = inventory.quantity

            except Inventory.DoesNotExist:
                self.fields["quantity"].initial = 0

        self.fields["category"].queryset = categories

        self.fields["discount_percentage"].required = False

    def clean_price(self):

        price = self.cleaned_data["price"]

        if price <= 0:
            raise forms.ValidationError(
                "Price must be greater than zero."
            )

        return price

    def clean_discount_percentage(self):

        discount = self.cleaned_data.get(
            "discount_percentage"
        )

        if discount is None:
            return Decimal("0.00")

        if discount < 0 or discount > 100:
            raise forms.ValidationError(
                "Discount must be between 0 and 100."
            )

        return discount

    def clean_quantity(self):

        quantity = self.cleaned_data.get("quantity")

        if quantity is None:
            return 0

        if quantity < 0:
            raise forms.ValidationError(
                "Quantity cannot be negative."
            )

        return quantity

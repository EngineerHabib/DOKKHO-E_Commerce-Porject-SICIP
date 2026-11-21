
from django import forms
from django.forms import inlineformset_factory, BaseInlineFormSet

from .models import Purchase, PurchaseItem
from suppliers.models import Supplier
from products.models import Product


class PurchaseForm(forms.ModelForm):

    class Meta:
        model = Purchase

        fields = [
            "supplier",
            "expected_delivery_date",
            "notes",
        ]

        widgets = {
            "supplier": forms.Select(attrs={
                "class": "form-select",
            }),

            "expected_delivery_date": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date",
            }),

            "notes": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Enter purchase notes...",
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["supplier"].queryset = Supplier.objects.filter(
            is_active=True
        ).order_by("company_name")


class PurchaseItemForm(forms.ModelForm):

    class Meta:
        model = PurchaseItem

        fields = [
            "product",
            "quantity",
            "unit_cost",
        ]

        widgets = {
            "product": forms.Select(attrs={
                "class": "form-select",
            }),

            "quantity": forms.NumberInput(attrs={
                "class": "form-control",
                "min": 1,
                "placeholder": "Enter quantity",
            }),

            "unit_cost": forms.NumberInput(attrs={
                "class": "form-control",
                "min": "0.01",
                "step": "0.01",
                "placeholder": "Enter purchase cost",
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["product"].queryset = Product.objects.filter(
            is_active=True
        ).order_by("name")


class BasePurchaseItemFormSet(BaseInlineFormSet):

    def clean(self):
        super().clean()

        if any(self.errors):
            return

        selected_products = []
        valid_items = 0

        for form in self.forms:

            if not form.cleaned_data:
                continue

            if form.cleaned_data.get("DELETE"):
                continue

            product = form.cleaned_data.get("product")

            if not product:
                continue

            valid_items += 1

            if product in selected_products:
                raise forms.ValidationError(
                    "A product cannot be added more than once."
                )

            selected_products.append(product)

        if valid_items == 0:
            raise forms.ValidationError(
                "Please add at least one product to the purchase."
            )


PurchaseItemFormSet = inlineformset_factory(
    Purchase,
    PurchaseItem,
    form=PurchaseItemForm,
    formset=BasePurchaseItemFormSet,
    extra=1,
    can_delete=True,
    min_num=1,
    validate_min=True,
)

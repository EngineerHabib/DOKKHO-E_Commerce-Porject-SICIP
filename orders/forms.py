
from django import forms

from .models import Order


class OrderCreateForm(forms.ModelForm):

    quantity = forms.IntegerField(
        min_value=1,
        initial=1,
        widget=forms.NumberInput(attrs={
            "class": "form-control",
            "min": 1,
            "step": 1,
        })
    )
    class Meta:
        model = Order

        fields = [
            "customer_name",
            "email",
            "phone",
            "shipping_address",
            "payment_method",
            "note",
        ]

        widgets = {
            "customer_name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter your full name",
            }),

            "email": forms.EmailInput(attrs={
                "class": "form-control",
                "placeholder": "Enter your email",
            }),

            "phone": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter your phone number",
            }),

            "shipping_address": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Enter your full delivery address",
            }),

            "payment_method": forms.Select(attrs={
                "class": "form-select",
            }),

            "note": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 2,
                "placeholder": "Additional instructions (optional)",
            }),
        }

        labels = {
            "customer_name": "Full Name",
            "email": "Email Address",
            "phone": "Phone Number",
            "shipping_address": "Delivery Address",
            "payment_method": "Payment Method",
            "note": "Order Note",
        }




class CartCheckoutForm(forms.Form):

    customer_name = forms.CharField(
        max_length=150,
        label="Full Name",
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Enter your full name",
        })
    )

    email = forms.EmailField(
        label="Email Address",
        widget=forms.EmailInput(attrs={
            "class": "form-control",
            "placeholder": "Enter your email address",
        })
    )

    phone = forms.CharField(
        max_length=20,
        label="Phone Number",
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "01XXXXXXXXX",
        })
    )

    shipping_address = forms.CharField(
        label="Delivery Address",
        widget=forms.Textarea(attrs={
            "class": "form-control",
            "rows": 3,
            "placeholder": "House, Road, Area, City, District",
        })
    )

    note = forms.CharField(
        required=False,
        label="Order Note (Optional)",
        widget=forms.Textarea(attrs={
            "class": "form-control",
            "rows": 2,
            "placeholder": "Any special instructions?",
        })
    )

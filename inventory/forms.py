
from django import forms

from .models import StockTransaction, Inventory


class StockTransactionForm(forms.ModelForm):

    class Meta:
        model = StockTransaction

        fields = [
            "transaction_type",
            "quantity",
            "note",
        ]

        widgets = {
            "transaction_type": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),

            "quantity": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter quantity",
                    "min": 1,
                }
            ),

            "note": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Enter transaction note (optional)",
                }
            ),
        }

        labels = {
            "transaction_type": "Transaction Type",
            "quantity": "Quantity",
            "note": "Note",
        }


class InventoryForm(forms.ModelForm):

    class Meta:
        model = Inventory

        fields = [
            "low_stock_threshold",
        ]

        widgets = {
            "low_stock_threshold": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 0,
                    "placeholder": "Enter low stock limit",
                }
            ),
        }

        labels = {
            "low_stock_threshold": "Low Stock Alert Limit",
        }

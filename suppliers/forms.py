
from django import forms
from .models import Supplier


class SupplierForm(forms.ModelForm):

    class Meta:
        model = Supplier
        fields = [
            "company_name",
            "contact_person",
            "email",
            "phone",
            "alternate_phone",
            "address",
            "city",
            "country",
            "notes",
            "is_active",
        ]

        widgets = {
            "company_name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter company name"
            }),
            "contact_person": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter contact person"
            }),
            "email": forms.EmailInput(attrs={
                "class": "form-control",
                "placeholder": "example@email.com"
            }),
            "phone": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter phone number"
            }),
            "alternate_phone": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter alternate phone"
            }),
            "address": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Enter full address"
            }),
            "city": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter city"
            }),
            "country": forms.TextInput(attrs={
                "class": "form-control"
            }),
            "notes": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Additional information"
            }),
        }

    def clean_phone(self):
        phone = self.cleaned_data["phone"].strip()

        if len(phone) < 7:
            raise forms.ValidationError("Phone number must contain at least 7 characters.")

        return phone

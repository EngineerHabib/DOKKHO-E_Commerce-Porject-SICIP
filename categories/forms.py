
from django import forms
from django.db.models import Q

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, Div

from .models import Category


class CategoryForm(forms.ModelForm):

    class Meta:
        model = Category

        fields = [
            "name",
            "description",
            "image",
            "is_active",
        ]

        widgets = {
            "name": forms.TextInput(attrs={
                "placeholder": "Enter category name",
            }),

            "description": forms.Textarea(attrs={
                "placeholder": "Enter category description",
                "rows": 4,
            }),

            "image": forms.ClearableFileInput(),

            "is_active": forms.CheckboxInput(),
        }

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        for field_name, field in self.fields.items():

            if field_name != "is_active":
                field.widget.attrs["class"] = "form-control"

        self.fields["is_active"].widget.attrs["class"] = (
            "form-check-input"
        )

        self.helper = FormHelper()
        self.helper.form_tag = False

    def clean_name(self):

        name = self.cleaned_data["name"].strip()

        duplicate = Category.objects.filter(
            name__iexact=name
        ).exclude(
            pk=self.instance.pk
        )

        if duplicate.exists():
            raise forms.ValidationError(
                "This category already exists."
            )

        return name

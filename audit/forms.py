
from django import forms
from .models import AuditLog


class AuditFilterForm(forms.Form):

    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Search user, object or activity..."
        })
    )

    action = forms.ChoiceField(
        required=False,
        choices=[("", "All Actions")] + list(AuditLog.Action.choices),
        widget=forms.Select(attrs={
            "class": "form-select"
        })
    )

    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            "type": "date",
            "class": "form-control"
        })
    )

    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            "type": "date",
            "class": "form-control"
        })
    )

    def clean(self):
        cleaned_data = super().clean()

        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")

        if start_date and end_date and start_date > end_date:
            raise forms.ValidationError(
                "Start date cannot be later than end date."
            )

        return cleaned_data

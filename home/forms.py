from django import forms


class NewsletterForm(forms.Form):

    email = forms.EmailField(
        max_length=254,
        widget=forms.EmailInput(attrs={
            "class": "newsletter-input",
            "placeholder": "Enter your email address",
            "required": True,
        })
    )

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()
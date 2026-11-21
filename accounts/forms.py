
from django import forms
from django.contrib.auth.forms import (
    UserCreationForm,
    AuthenticationForm,
)

from .models import User


# Available roles for Super Admin to assign
MANAGEABLE_ROLES = [
    choice for choice in User.Role.choices
    if choice[0] != User.Role.SUPER_ADMIN
]


class RegistrationForm(UserCreationForm):

    email = forms.EmailField(
        label="Email Address",
        widget=forms.EmailInput(attrs={
            "placeholder": "Enter your email address",
        })
    )

    phone = forms.CharField(
        label="Phone Number",
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            "placeholder": "Enter your phone number",
        })
    )

    class Meta:
        model = User

        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "phone",
            "password1",
            "password2",
        ]

        widgets = {
            "username": forms.TextInput(attrs={
                "placeholder": "Enter username",
            }),
            "first_name": forms.TextInput(attrs={
                "placeholder": "Enter first name",
            }),
            "last_name": forms.TextInput(attrs={
                "placeholder": "Enter last name",
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field_name, field in self.fields.items():
            field.widget.attrs["class"] = "form-control"

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()

        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "This email address is already registered."
            )

        return email

    def clean_phone(self):
        phone = self.cleaned_data.get("phone", "").strip()

        if not phone:
            return None

        if User.objects.filter(phone=phone).exists():
            raise forms.ValidationError(
                "This phone number is already registered."
            )

        return phone


class LoginForm(AuthenticationForm):

    username = forms.CharField(
        label="Username or Email",
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Enter username or email",
            "autofocus": True,
        })
    )

    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "Enter your password",
        })
    )


# SUPER ADMIN: CREATE USER
class UserManagementCreateForm(UserCreationForm):

    role = forms.ChoiceField(
        choices=MANAGEABLE_ROLES,
        label="User Role",
        widget=forms.Select(attrs={
            "class": "form-select",
        })
    )

    email = forms.EmailField(
        label="Email Address",
        widget=forms.EmailInput(attrs={
            "class": "form-control",
            "placeholder": "Enter email address",
        })
    )

    phone = forms.CharField(
        label="Phone Number",
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Enter phone number",
        })
    )

    address = forms.CharField(
        label="Address",
        required=False,
        widget=forms.Textarea(attrs={
            "class": "form-control",
            "rows": 3,
            "placeholder": "Enter address",
        })
    )

    profile_image = forms.ImageField(
        label="Profile Image",
        required=False,
        widget=forms.ClearableFileInput(attrs={
            "class": "form-control",
        })
    )

    class Meta:
        model = User

        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "phone",
            "role",
            "address",
            "profile_image",
            "password1",
            "password2",
        ]

        widgets = {
            "username": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter username",
            }),
            "first_name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter first name",
            }),
            "last_name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter last name",
            }),
        }

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()

        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "This email address is already registered."
            )

        return email

    def clean_phone(self):
        phone = self.cleaned_data.get("phone", "").strip()

        if not phone:
            return None

        if User.objects.filter(phone=phone).exists():
            raise forms.ValidationError(
                "This phone number is already registered."
            )

        return phone

    def save(self, commit=True):
        user = super().save(commit=False)

        user.role = self.cleaned_data["role"]
        user.is_staff = False
        user.is_superuser = False

        if commit:
            user.save()

        return user


# SUPER ADMIN: UPDATE USER
class UserManagementUpdateForm(forms.ModelForm):

    role = forms.ChoiceField(
        choices=MANAGEABLE_ROLES,
        label="User Role",
        widget=forms.Select(attrs={
            "class": "form-select",
        })
    )

    class Meta:
        model = User

        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "phone",
            "role",
            "address",
            "profile_image",
            "is_active",
        ]

        widgets = {
            "username": forms.TextInput(attrs={
                "class": "form-control",
            }),
            "first_name": forms.TextInput(attrs={
                "class": "form-control",
            }),
            "last_name": forms.TextInput(attrs={
                "class": "form-control",
            }),
            "email": forms.EmailInput(attrs={
                "class": "form-control",
            }),
            "phone": forms.TextInput(attrs={
                "class": "form-control",
            }),
            "address": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
            }),
            "profile_image": forms.ClearableFileInput(attrs={
                "class": "form-control",
            }),
            "is_active": forms.CheckboxInput(attrs={
                "class": "form-check-input",
            }),
        }

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()

        if User.objects.filter(
            email__iexact=email
        ).exclude(pk=self.instance.pk).exists():

            raise forms.ValidationError(
                "This email address is already registered."
            )

        return email

    def clean_phone(self):
        phone = self.cleaned_data.get("phone", "").strip()

        if not phone:
            return None

        if User.objects.filter(
            phone=phone
        ).exclude(pk=self.instance.pk).exists():

            raise forms.ValidationError(
                "This phone number is already registered."
            )

        return phone

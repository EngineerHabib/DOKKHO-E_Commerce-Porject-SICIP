
from django import forms

from .models import Review


class ReviewForm(forms.ModelForm):

    class Meta:
        model = Review

        fields = [
            "rating",
            "title",
            "comment",
        ]

        widgets = {
            "rating": forms.Select(
                attrs={
                    "class": "form-select",
                    "required": True,
                }
            ),

            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Write a short review title",
                    "maxlength": 150,
                    "required": True,
                }
            ),

            "comment": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 5,
                    "placeholder": "Share your experience with this product...",
                    "required": True,
                }
            ),
        }

        labels = {
            "rating": "Your Rating",
            "title": "Review Title",
            "comment": "Your Review",
        }

    def clean_rating(self):

        rating = self.cleaned_data.get("rating")

        try:
            rating = int(rating)
        except (TypeError, ValueError):
            raise forms.ValidationError(
                "Please select a valid rating."
            )

        if rating not in [1, 2, 3, 4, 5]:
            raise forms.ValidationError(
                "Please select a rating between 1 and 5 stars."
            )

        return rating

    def clean_title(self):

        title = self.cleaned_data.get("title", "").strip()

        if not title:
            raise forms.ValidationError(
                "Review title is required."
            )

        return title

    def clean_comment(self):

        comment = self.cleaned_data.get("comment", "").strip()

        if not comment:
            raise forms.ValidationError(
                "Review comment is required."
            )

        return comment

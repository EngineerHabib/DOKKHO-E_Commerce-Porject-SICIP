
from django.db import models
from django.conf import settings
from django.utils.text import slugify


class Category(models.Model):

    name = models.CharField(
        max_length=150,
        unique=True
    )

    slug = models.SlugField(
        max_length=180,
        unique=True,
        blank=True
    )

    description = models.TextField(
        blank=True,
        null=True
    )

    image = models.ImageField(
        upload_to="categories/",
        blank=True,
        null=True
    )

    is_active = models.BooleanField(
        default=True
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_categories"
    )

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_categories"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "Category"
        verbose_name_plural = "Categories"

    def save(self, *args, **kwargs):

        if not self.slug:
            base_slug = slugify(self.name)
            unique_slug = base_slug
            counter = 1

            while Category.objects.filter(
                slug=unique_slug
            ).exclude(pk=self.pk).exists():

                counter += 1
                unique_slug = f"{base_slug}-{counter}"

            self.slug = unique_slug

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


from functools import wraps

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.views.decorators.http import require_POST

from products.models import Product
from orders.models import Order
from .models import Review
from .forms import ReviewForm


# Customer Permission
def customer_required(view_func):

    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):

        if getattr(request.user, "role", None) == "customer":
            return view_func(request, *args, **kwargs)

        raise PermissionDenied(
            "Only customers can manage product reviews."
        )

    return wrapper


# Verified Purchase Check
def has_delivered_purchase(user, product):

    return Order.objects.filter(
        customer=user,
        status=Order.Status.DELIVERED,
        items__product=product
    ).exists()


# Create Review
@customer_required
def review_create(request, slug):

    product = get_object_or_404(
        Product,
        slug=slug,
        is_active=True
    )

    # Verify delivered purchase
    if not has_delivered_purchase(request.user, product):

        messages.error(
            request,
            "You can review this product only after receiving it."
        )

        return redirect(
            "products:product_detail",
            slug=product.slug
        )

    # Check existing review
    existing_review = Review.objects.filter(
        product=product,
        user=request.user
    ).first()

    if existing_review:

        messages.info(
            request,
            "You have already reviewed this product. You can update your review."
        )

        return redirect(
            "reviews:review_update",
            slug=product.slug,
            review_id=existing_review.pk
        )

    form = ReviewForm(request.POST or None)

    if request.method == "POST":

        if form.is_valid():

            review = form.save(commit=False)

            review.product = product
            review.user = request.user

            # Automatically approve review
            review.is_approved = True

            review.save()

            messages.success(
                request,
                "Your review and rating have been submitted successfully!"
            )

            return redirect(
                "products:product_detail",
                slug=product.slug
            )

        messages.error(
            request,
            "Please correct the errors in the review form."
        )

    context = {
        "form": form,
        "product": product,
        "title": "Write a Review",
    }

    return render(
        request,
        "reviews/review_form.html",
        context
    )


# Update Own Review
@customer_required
def review_update(request, slug, review_id):

    review = get_object_or_404(
        Review,
        pk=review_id,
        product__slug=slug,
        user=request.user
    )

    form = ReviewForm(
        request.POST or None,
        instance=review
    )

    if request.method == "POST":

        if form.is_valid():

            updated_review = form.save(commit=False)

            # Keep review automatically approved
            updated_review.is_approved = True

            updated_review.save()

            messages.success(
                request,
                "Your review has been updated successfully!"
            )

            return redirect(
                "products:product_detail",
                slug=review.product.slug
            )

        messages.error(
            request,
            "Please correct the errors in the review form."
        )

    context = {
        "form": form,
        "product": review.product,
        "title": "Update Review",
    }

    return render(
        request,
        "reviews/review_form.html",
        context
    )


# Delete Own Review
@customer_required
@require_POST
def review_delete(request, slug, review_id):

    review = get_object_or_404(
        Review,
        pk=review_id,
        product__slug=slug,
        user=request.user
    )

    product_slug = review.product.slug

    review.delete()

    messages.success(
        request,
        "Your review has been deleted successfully."
    )

    return redirect(
        "products:product_detail",
        slug=product_slug
    )

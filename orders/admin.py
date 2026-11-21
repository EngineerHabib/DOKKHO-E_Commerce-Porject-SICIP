
from django.contrib import admin

from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = (
        "product",
        "product_name",
        "product_sku",
        "quantity",
        "unit_price",
        "line_total",
    )
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):

    list_display = (
        "order_number",
        "customer_name",
        "phone",
        "total_amount",
        "status",
        "payment_status",
        "created_at",
    )

    list_filter = (
        "status",
        "payment_method",
        "payment_status",
        "created_at",
    )

    search_fields = (
        "order_number",
        "customer_name",
        "email",
        "phone",
    )

    readonly_fields = (
        "order_number",
        "customer",
        "customer_name",
        "email",
        "phone",
        "shipping_address",
        "subtotal",
        "delivery_charge",
        "total_amount",
        "created_at",
        "updated_at",
    )

    inlines = [OrderItemInline]

    list_per_page = 20


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):

    list_display = (
        "order",
        "product_name",
        "product_sku",
        "quantity",
        "unit_price",
        "line_total",
    )

    search_fields = (
        "order__order_number",
        "product_name",
        "product_sku",
    )

    readonly_fields = (
        "order",
        "product",
        "product_name",
        "product_sku",
        "quantity",
        "unit_price",
        "line_total",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

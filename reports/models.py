
from django.db import models
from django.conf import settings


class ReportLog(models.Model):

    class ReportType(models.TextChoices):
        SALES = "SALES", "Sales Report"
        ORDER = "ORDER", "Order Report"
        PRODUCT = "PRODUCT", "Product Report"
        INVENTORY = "INVENTORY", "Inventory Report"
        PURCHASE = "PURCHASE", "Purchase Report"

    report_type = models.CharField(
        max_length=20,
        choices=ReportType.choices
    )

    start_date = models.DateField(
        null=True,
        blank=True
    )

    end_date = models.DateField(
        null=True,
        blank=True
    )

    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="generated_reports"
    )

    exported_as = models.CharField(
        max_length=20,
        default="VIEW",
        choices=[
            ("VIEW", "Viewed"),
            ("CSV", "CSV"),
            ("PDF", "PDF"),
            ("EXCEL", "Excel"),
        ]
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Report Log"
        verbose_name_plural = "Report Logs"

    def __str__(self):
        return (
            f"{self.get_report_type_display()} - "
            f"{self.created_at:%d %b %Y}"
        )

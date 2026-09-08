"""Models for the Invoice app."""

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models, transaction
from base.manager import SoftDeleteModel
from base.utility import generate_unique_code
from customer.models import Customer
from jobcard.models import JobCard
from inventory.models import Inventory


class Invoice(SoftDeleteModel):
    """Invoice for billing customers after job card completion or counter sales"""

    invoice_number = models.CharField(max_length=20, unique=True, editable=False)
    customer = models.ForeignKey(
        Customer, on_delete=models.PROTECT, related_name="invoices"
    )
    job_card = models.ForeignKey(
        JobCard,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invoices",
        help_text="Source job card (leave blank for counter sales)",
    )

    # Status & payment

    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Final amount = subtotal + tax - discount",
    )

    notes = models.TextField(blank=True, default="")

    # Metadata
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        """Meta options for Invoice"""

        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["customer"]),
            models.Index(fields=["job_card"]),
        ]

    def create_invoice_number(self, save=True):
        """
        Generate and assign a unique invoice number (e.g., INV0001).
        """
        if not self.invoice_number:
            self.invoice_number = generate_unique_code("INV", Invoice, "invoice_number", 4)
            if save and self.pk:
                super(Invoice, self).save(update_fields=["invoice_number"])
        return self.invoice_number

    def save(self, *args, **kwargs):
        with transaction.atomic():
            if not self.invoice_number:
                self.invoice_number = generate_unique_code("INV", Invoice, "invoice_number", 4)
            super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.invoice_number} - {self.customer.name}"


class InvoiceItem(models.Model):
    """Individual billable items on an invoice"""

    invoice = models.ForeignKey(
        Invoice, on_delete=models.CASCADE, related_name="invoice_items"
    )
    inventory = models.ForeignKey(
        Inventory,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="invoice_usages",
        help_text="Linked spare part (leave blank for labour charges)",
    )
    description = models.CharField(
        max_length=255, help_text="e.g., 'Oil Filter' or 'Labour - Engine Repair'"
    )

    quantity = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0)]
    )
    unit_price = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0)]
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Meta options for Invoice Item"""

        ordering = ["id"]

    def __str__(self):
        # pylint: disable=no-member
        return f"{self.invoice.invoice_number} - {self.description} x {self.quantity}"

    @property
    def total_price(self):
        """Calculate total price for this line item (quantity × unit_price)"""
        return self.quantity * self.unit_price

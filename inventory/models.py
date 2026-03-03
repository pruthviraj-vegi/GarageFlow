"""Models for the inventory application."""

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from base.manager import SoftDeleteModel
from vehicle.models import VehicleModel


class Category(SoftDeleteModel):
    """Category for organizing spare parts"""

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, default="")
    parent = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="subcategories",
    )
    # Metadata
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        """Meta options for the Category model."""

        verbose_name_plural = "Categories"
        ordering = ["name"]

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name


class UOM(SoftDeleteModel):
    """Unit of Measurement for spare parts"""

    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, default="")
    # Metadata
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        """Meta options for the UOM model."""

        verbose_name_plural = "Units of Measurement"
        ordering = ["name"]

    def __str__(self):
        return str(self.name)


class Inventory(SoftDeleteModel):
    """Main inventory item - Car Spare Parts"""

    brand = models.CharField(max_length=100, null=True, blank=True)
    name = models.CharField(max_length=200)
    part_number = models.CharField(max_length=100, null=True, blank=True)
    barcode = models.CharField(
        max_length=100,
        unique=True,
        blank=True,
        help_text="Auto-generated barcode for part tracking",
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        related_name="spare_parts",
        null=True,
        blank=True,
    )
    uom = models.ForeignKey(
        UOM,
        on_delete=models.SET_NULL,
        related_name="spare_parts",
        null=True,
        blank=True,
    )

    # Compatibility information - Link to VehicleModel master data
    compatible_vehicles = models.ManyToManyField(
        VehicleModel,
        related_name="compatible_parts",
        blank=True,
        help_text="Select all compatible vehicle models",
    )

    # Alternative: Free text for universal parts or when specific model not in database
    compatibility_notes = models.TextField(
        blank=True,
        default="",
        help_text="Additional compatibility info or if this is a universal part",
    )

    # Pricing
    cost_price = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0)]
    )
    selling_price = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0)]
    )

    # Inventory tracking
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    low_stock = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)]
    )

    # Storage location
    shelf_location = models.CharField(
        max_length=50, blank=True, default="", help_text="e.g., A1-B2"
    )

    description = models.TextField(blank=True, default="")

    # Metadata
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        """Meta options for the Inventory model."""

        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["name"]),
        ]

    def __str__(self):
        return f"{self.brand} {self.name}"

    def create_barcode(self, save=True):
        """
        Auto-generate a barcode based on the object's primary key.
        Only called when no barcode is provided from the frontend.

        Returns:
            str: The newly created barcode
        """
        if not self.pk:
            super(Inventory, self).save()

        self.barcode = f"{self.pk:06d}3"

        if save:
            super(Inventory, self).save(update_fields=["barcode"])

        return self.barcode

    def save(self, *args, **kwargs):
        if not self.pk and not self.barcode:
            super(Inventory, self).save(*args, **kwargs)
            self.create_barcode(save=True)
        else:
            super(Inventory, self).save(*args, **kwargs)

    @property
    def profit_margin(self):
        """Calculate profit margin percentage"""
        if self.cost_price > 0:
            return ((self.selling_price - self.cost_price) / self.cost_price) * 100
        return 0

    def get_compatible_vehicles_display(self):
        """Get a readable list of compatible vehicles"""
        # pylint: disable=no-member
        return ", ".join([str(v) for v in self.compatible_vehicles.all()[:5]])

    @property
    def reserved_quantity(self):
        """Calculate quantity reserved in pending job cards."""
        # pylint: disable=no-member
        result = self.job_card_usages.filter(job_card__status="pending").aggregate(
            total=models.Sum("quantity")
        )
        return result.get("total") or 0

    @property
    def available_quantity(self):
        """Calculate available quantity"""
        return self.quantity - self.reserved_quantity

    @property
    def is_low_stock(self):
        """Check if stock is low"""
        if self.low_stock == 0:
            return False
        return self.available_quantity <= self.low_stock


class InventoryLog(SoftDeleteModel):
    """Track all stock movements - purchases, sales, returns, adjustments"""

    class TransactionType(models.TextChoices):
        """Choices for inventory transaction types."""

        PURCHASE = "purchase", "Purchase/Stock In"
        SALE = "sale", "Sale/Stock Out"
        RETURN = "return", "Customer Return"
        ADJUSTMENT = "adjustment", "Stock Adjustment"
        DAMAGE = "damage", "Damaged/Written Off"

    inventory = models.ForeignKey(
        Inventory, on_delete=models.PROTECT, related_name="inventory_logs"
    )
    transaction_type = models.CharField(max_length=20, choices=TransactionType.choices)

    quantity = models.IntegerField(
        help_text="Positive for stock in, negative for stock out"
    )
    reference_number = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="PO number, Invoice number, etc.",
    )

    invoice_item = models.ForeignKey(
        "invoice.InvoiceItem",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Link to job card if applicable",
    )

    notes = models.TextField(blank=True, null=True)
    transaction_date = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        """Meta options for the InventoryLog model."""

        ordering = ["-transaction_date"]
        indexes = [
            models.Index(fields=["transaction_type"]),
            models.Index(fields=["transaction_date"]),
        ]

    def __str__(self):
        return f"{self.transaction_type} - {self.inventory.name} - Qty: {self.quantity}"

"""Models for the Job Card app."""

from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.db.models import Sum, F
from base.manager import SoftDeleteModel
from base.utility import generate_unique_code
from customer.models import Customer
from vehicle.models import VehicleModel
from inventory.models import Inventory

# Create your models here.


class JobCard(SoftDeleteModel):
    """Job Card for service/repair work"""

    class Status(models.TextChoices):
        """Status choices for Job Card"""

        PENDING = "pending", "Pending"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    job_card_number = models.CharField(max_length=20, unique=True, editable=False)
    customer = models.ForeignKey(
        Customer, on_delete=models.PROTECT, related_name="job_cards"
    )
    vehicle_model = models.ForeignKey(
        VehicleModel,
        on_delete=models.PROTECT,
        related_name="job_cards",
        null=True,
        blank=True,
        help_text="Link to vehicle master data (make/model/variant)",
    )
    vehicle_number = models.CharField(
        max_length=20, help_text="Vehicle registration/plate number"
    )

    # Job details
    odometer_reading = models.IntegerField(
        blank=True,
        null=True,
        help_text="Current odometer reading in km",
        validators=[MinValueValidator(0)],
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True
    )

    # Status tracking timestamps
    completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    # metadata
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        """Meta options"""

        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["vehicle_model"]),
            models.Index(fields=["customer"]),
            models.Index(fields=["vehicle_number"]),
        ]

    def create_job_card_number(self, save=True):
        """
        Generate and assign a unique job card number (e.g., JC0001).
        """
        if not self.job_card_number:
            self.job_card_number = generate_unique_code("JC", JobCard, "job_card_number", 4)
            if save and self.pk:
                super(JobCard, self).save(update_fields=["job_card_number"])
        return self.job_card_number

    def save(self, *args, **kwargs):
        # Track status transition timestamps
        if self.pk:
            try:
                old = JobCard.objects.get(pk=self.pk)
                if old.status != self.status:
                    if self.status == self.Status.COMPLETED:
                        self.completed_at = timezone.now()
                    elif self.status == self.Status.CANCELLED:
                        self.cancelled_at = timezone.now()
            except ObjectDoesNotExist:
                pass

        with transaction.atomic():
            if not self.job_card_number:
                self.job_card_number = generate_unique_code("JC", JobCard, "job_card_number", 4)
            super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.job_card_number} - {self.vehicle_number}"

    @property
    def get_total_price(self):
        """Calculate total price for this job card"""
        # pylint: disable=no-member
        result = self.job_card_items.aggregate(
            total=Sum(F("quantity") * F("unit_price"))
        )
        return result["total"] or 0


class JobCardItem(models.Model):
    """Individual parts used in a job card"""

    job_card = models.ForeignKey(
        JobCard, on_delete=models.CASCADE, related_name="job_card_items"
    )
    inventory = models.ForeignKey(
        Inventory, on_delete=models.PROTECT, related_name="job_card_usages"
    )

    quantity = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0)]
    )
    unit_price = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0)]
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Meta options for Job Card Item"""

        ordering = ["-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["job_card", "inventory"],
                name="unique_jobcard_inventory",
            )
        ]

    def __str__(self):
        # pylint: disable=no-member
        return (
            f"{self.job_card.job_card_number} - {self.inventory.name} x {self.quantity}"
        )

    @property
    def total_price(self):
        """Calculate total price for this line item (quantity × unit_price)"""
        base_price = self.quantity * self.unit_price
        return base_price

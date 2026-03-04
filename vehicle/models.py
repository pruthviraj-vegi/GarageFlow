"""
Models for managing vehicle makes and models.
"""

from django.conf import settings
from django.db import models
from base.manager import SoftDeleteModel


class VehicleMake(SoftDeleteModel):
    """Master table for vehicle manufacturers"""

    name = models.CharField(
        max_length=100, unique=True, help_text="e.g., Toyota, Honda, Maruti Suzuki"
    )

    # Metadata
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        """Meta options for VehicleMake model."""

        ordering = ["name"]

    def __str__(self):
        return str(self.name)


class VehicleModel(SoftDeleteModel):
    """Master table for vehicle models and variants"""

    class FuelTypeChoices(models.TextChoices):
        """Choices for vehicle fuel type."""

        PETROL = "petrol", "Petrol"
        DIESEL = "diesel", "Diesel"
        ELECTRIC = "electric", "Electric"
        HYBRID = "hybrid", "Hybrid"
        CNG = "cng", "CNG"

    class TransmissionChoices(models.TextChoices):
        """Choices for vehicle transmission type."""

        MANUAL = "manual", "Manual"
        AUTOMATIC = "automatic", "Automatic"
        SEMI_AUTOMATIC = "semi_automatic", "Semi-Automatic"
        CVT = "cvt", "CVT"

    make = models.ForeignKey(
        VehicleMake, on_delete=models.PROTECT, related_name="models"
    )
    model_name = models.CharField(max_length=100, help_text="e.g., Innova, City, Swift")

    # Technical specifications
    fuel_type = models.CharField(max_length=20, choices=FuelTypeChoices.choices)
    transmission = models.CharField(max_length=20, choices=TransmissionChoices.choices)

    notes = models.TextField(blank=True, default="")

    # Metadata
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        """Meta options for VehicleModel model."""

        ordering = ["make__name", "model_name"]
        indexes = [
            models.Index(fields=["make", "model_name"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "make",
                    "model_name",
                    "fuel_type",
                    "transmission",
                ],
                name="unique_vehicle_model_combination",
            )
        ]

    def __str__(self):
        return f"{self.make.name} {self.model_name} ({self.fuel_type} - {self.transmission})"

    @property
    def display_name(self):
        """Short display name without year"""
        return f"{self.make.name} {self.model_name}"

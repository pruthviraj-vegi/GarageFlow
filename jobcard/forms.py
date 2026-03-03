"""Forms for the Job Card application."""

import re

from django import forms
from .models import JobCard


class JobCardForm(forms.ModelForm):
    """Form for creating and updating Job Cards."""

    class Meta:
        """Meta options for the JobCardForm."""

        model = JobCard
        fields = [
            "customer",
            "vehicle_model",
            "vehicle_number",
            "odometer_reading",
            "status",
        ]
        widgets = {
            "customer": forms.Select(attrs={"class": "form-select"}),
            "vehicle_model": forms.Select(attrs={"class": "form-select"}),
            "vehicle_number": forms.TextInput(
                attrs={"class": "form-input", "placeholder": "e.g. KA-01-AB-1234"}
            ),
            "odometer_reading": forms.NumberInput(
                attrs={"class": "form-input", "placeholder": "Current Odometer (km)"}
            ),
            "status": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # On validation errors, move autofocus to the first errored field
        if self.errors:
            for field in self.fields.values():
                field.widget.attrs.pop("autofocus", None)
            for field_name in self.fields:
                if field_name in self.errors:
                    self.fields[field_name].widget.attrs["autofocus"] = True
                    break

        if not self.instance.pk:
            self.fields["status"].required = False
            # Ensure status is set to pending if not provided by the UI form
            if not getattr(self, "cleaned_data", {}).get("status"):
                self.instance.status = JobCard.Status.PENDING

    def clean(self):
        cleaned_data = super().clean()
        if not self.instance.pk:
            # If status is missing for a new JobCard, remove the error
            if "status" in self.errors:
                del self.errors["status"]
            cleaned_data["status"] = JobCard.Status.PENDING

        # Prevent duplicate pending/in-progress job cards for the same vehicle
        vehicle_number = cleaned_data.get("vehicle_number")
        if vehicle_number:
            existing = JobCard.objects.filter(
                vehicle_number=vehicle_number,
                status__in=[JobCard.Status.PENDING, JobCard.Status.IN_PROGRESS],
            )
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            if existing.exists():
                jc = existing.first()
                raise forms.ValidationError(
                    f"Vehicle {vehicle_number} already has an active job card "
                    f"({jc.job_card_number} — {jc.get_status_display()}). "
                    f"Please complete or cancel it before creating a new one."
                )

        return cleaned_data

    # ─── Customer validation ───
    def clean_customer(self):
        """Validate the customer field."""
        customer = self.cleaned_data.get("customer")
        if not customer:
            raise forms.ValidationError("Customer is required.")
        return customer

    # ─── Vehicle number validation ───
    def clean_vehicle_number(self):
        """Validate the vehicle number field."""
        vehicle_number = self.cleaned_data.get("vehicle_number", "").strip().upper()
        if not vehicle_number:
            raise forms.ValidationError("Vehicle number is required.")
        if len(vehicle_number) < 4:
            raise forms.ValidationError("Vehicle number must be at least 4 characters.")
        if len(vehicle_number) > 20:
            raise forms.ValidationError("Vehicle number must not exceed 20 characters.")
        if not re.match(r"^[A-Z0-9\-\s]+$", vehicle_number):
            raise forms.ValidationError(
                "Vehicle number can only contain letters, numbers, hyphens, and spaces."
            )
        return vehicle_number

    # ─── Odometer reading validation ───
    def clean_odometer_reading(self):
        """Validate the odometer reading field."""
        odometer = self.cleaned_data.get("odometer_reading")
        if odometer is not None:
            if odometer < 0:
                raise forms.ValidationError("Odometer reading cannot be negative.")
            if odometer > 9999999:
                raise forms.ValidationError(
                    "Odometer reading seems too high. Please verify."
                )
        return odometer

    # ─── Status validation ───
    def clean_status(self):
        """Validate the status field."""
        status = self.cleaned_data.get("status")
        # If no status is provided and this is a new job card, default to Pending
        if not status and not self.instance.pk:
            status = JobCard.Status.PENDING

        if status and self.instance and self.instance.pk:
            old_status = JobCard.objects.get(pk=self.instance.pk).status
            # Prevent reopening cancelled/completed jobs back to pending
            if (
                old_status
                in (
                    JobCard.Status.COMPLETED,
                    JobCard.Status.CANCELLED,
                )
                and status == JobCard.Status.PENDING
            ):
                raise forms.ValidationError(
                    f"Cannot revert a {old_status} job card back to Pending."
                )
        return status

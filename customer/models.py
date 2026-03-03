from django.conf import settings
from django.db import models
from base.manager import SoftDeleteModel
from base.utility import phone_regex


class Customer(SoftDeleteModel):
    """Customer/Member model for tracking client details"""

    customer_id = models.CharField(max_length=20, unique=True, editable=False)
    name = models.CharField(max_length=100)
    phone = models.CharField(validators=[phone_regex], max_length=10, unique=True)
    address = models.CharField(max_length=255, null=True, blank=True)

    # Metadata
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["phone"]),
        ]

    def create_customer_id(self, save=True):
        """
        Create a new customer ID based on the object's primary key.

        Args:
            save (bool): Whether to save the customer_id to the database.

        Returns:
            str: The newly created customer ID (e.g., CUST0001)
        """
        if not self.pk:
            super(Customer, self).save()

        self.customer_id = f"CUST{self.pk:04d}"

        if save:
            super(Customer, self).save(update_fields=["customer_id"])

        return self.customer_id

    def save(self, *args, **kwargs):
        if not self.pk and not self.customer_id:
            super().save(*args, **kwargs)
            self.create_customer_id(save=True)
        else:
            super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} - {self.phone}"

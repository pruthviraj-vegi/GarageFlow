from django.conf import settings
from django.db import models
from base.manager import SoftDeleteModel
from base.utility import phone_regex, generate_unique_code


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
        Generate and assign a unique customer ID (e.g., CUST0001).
        """
        if not self.customer_id:
            self.customer_id = generate_unique_code("CUST", Customer, "customer_id", 4)
            if save and self.pk:
                super(Customer, self).save(update_fields=["customer_id"])
        return self.customer_id

    def save(self, *args, **kwargs):
        if not self.customer_id:
            self.customer_id = generate_unique_code("CUST", Customer, "customer_id", 4)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} - {self.phone}"

"""Services for the inventory application."""

from django.db import transaction
from django.core.exceptions import ValidationError
from .models import InventoryLog


class InventoryService:
    """Service class for handling inventory logic and transactions."""

    @staticmethod
    @transaction.atomic
    def record_purchase(
        inventory, quantity, reference_number=None, notes=None, user=None
    ):
        """
        Record a purchase/stock-in for an inventory item and update its quantity.
        """
        if quantity <= 0:
            raise ValidationError("Purchase quantity must be greater than zero.")

        # Create the log entry
        log = InventoryLog.objects.create(
            inventory=inventory,
            transaction_type=InventoryLog.TransactionType.PURCHASE,
            quantity=quantity,
            reference_number=reference_number,
            notes=notes,
            created_by=user,
        )

        # Update the inventory object
        inventory.quantity += quantity
        inventory.save(update_fields=["quantity"])

        return log

    @staticmethod
    @transaction.atomic
    def record_sale(
        inventory,
        quantity,
        invoice_item=None,
        reference_number=None,
        notes=None,
        user=None,
    ):
        """
        Record a sale/stock-out for an inventory item and update its quantity.
        """
        if quantity <= 0:
            raise ValidationError("Sale quantity must be greater than zero.")

        if inventory.quantity < quantity:
            # We could raise an error or allow negative inventory depending on business logic.
            # Assuming we allow it and just log it for now, or just let it go negative.
            pass

        # Create the log entry (quantity is negative for stock out)
        log = InventoryLog.objects.create(
            inventory=inventory,
            transaction_type=InventoryLog.TransactionType.SALE,
            quantity=-quantity,  # Negative for sales
            invoice_item=invoice_item,
            reference_number=reference_number,
            notes=notes,
            created_by=user,
        )

        # Update the inventory object
        inventory.quantity -= quantity
        inventory.save(update_fields=["quantity"])

        return log

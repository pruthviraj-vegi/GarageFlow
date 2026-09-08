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
        Acquires a row-level lock on the item to prevent race conditions.
        """
        if quantity <= 0:
            raise ValidationError("Purchase quantity must be greater than zero.")

        # Lock inventory row
        locked_inv = inventory.__class__.objects.select_for_update().get(pk=inventory.pk)

        # Create the log entry
        log = InventoryLog.objects.create(
            inventory=locked_inv,
            transaction_type=InventoryLog.TransactionType.PURCHASE,
            quantity=quantity,
            reference_number=reference_number,
            notes=notes,
            created_by=user,
        )

        # Update quantity
        locked_inv.quantity += quantity
        locked_inv.save(update_fields=["quantity"])

        # Sync in-memory instance
        inventory.quantity = locked_inv.quantity

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
        allow_negative=True,
    ):
        """
        Record a sale/stock-out for an inventory item and update its quantity.
        Acquires a row-level lock on the item to prevent race conditions.
        """
        if quantity <= 0:
            raise ValidationError("Sale quantity must be greater than zero.")

        # Lock inventory row
        locked_inv = inventory.__class__.objects.select_for_update().get(pk=inventory.pk)

        if not allow_negative and locked_inv.quantity < quantity:
            raise ValidationError(
                f"Insufficient stock for {locked_inv.name}. Available: {locked_inv.quantity}, Requested: {quantity}."
            )

        # Create the log entry (quantity is negative for stock out)
        log = InventoryLog.objects.create(
            inventory=locked_inv,
            transaction_type=InventoryLog.TransactionType.SALE,
            quantity=-quantity,  # Negative for sales
            invoice_item=invoice_item,
            reference_number=reference_number,
            notes=notes,
            created_by=user,
        )

        # Update quantity
        locked_inv.quantity -= quantity
        locked_inv.save(update_fields=["quantity"])

        # Sync in-memory instance
        inventory.quantity = locked_inv.quantity

        return log

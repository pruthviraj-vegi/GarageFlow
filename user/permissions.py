"""
GarageFlow Role & Permission Definitions.

Provides pre-defined groups and permission mapping for Garage operations:
- Administrator: Full system access across all modules.
- Service Advisor / Service Manager: Handles customers, vehicles, job cards, invoices, view inventory.
- Inventory Manager: Manages stock items, categories, units of measure, and views operational docs.
- Cashier / Billing: Manages invoices and views customers/job cards.
- Technician / Mechanic: Views job cards, updates job card items, views vehicles/inventory.

Also supports dynamically creating any custom group in Django with custom permissions.
"""

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
import logging

logger = logging.getLogger(__name__)

# Group Names Constants
GROUP_ADMIN = "Administrator"
GROUP_SERVICE_ADVISOR = "Service Advisor"
GROUP_INVENTORY_MANAGER = "Inventory Manager"
GROUP_BILLING = "Cashier"
GROUP_TECHNICIAN = "Technician"

DEFAULT_GROUP_PERMISSIONS = {
    GROUP_ADMIN: [
        # Full access
        "user.view_dashboard",
        "customer.add_customer", "customer.change_customer", "customer.delete_customer", "customer.view_customer",
        "vehicle.add_vehiclemodel", "vehicle.change_vehiclemodel", "vehicle.delete_vehiclemodel", "vehicle.view_vehiclemodel",
        "vehicle.add_vehiclemake", "vehicle.change_vehiclemake", "vehicle.delete_vehiclemake", "vehicle.view_vehiclemake",
        "jobcard.add_jobcard", "jobcard.change_jobcard", "jobcard.delete_jobcard", "jobcard.view_jobcard",
        "jobcard.add_jobcarditem", "jobcard.change_jobcarditem", "jobcard.delete_jobcarditem", "jobcard.view_jobcarditem",
        "invoice.add_invoice", "invoice.change_invoice", "invoice.delete_invoice", "invoice.view_invoice",
        "invoice.add_invoiceitem", "invoice.change_invoiceitem", "invoice.delete_invoiceitem", "invoice.view_invoiceitem",
        "inventory.add_inventory", "inventory.change_inventory", "inventory.delete_inventory", "inventory.view_inventory",
        "inventory.add_category", "inventory.change_category", "inventory.delete_category", "inventory.view_category",
        "inventory.add_uom", "inventory.change_uom", "inventory.delete_uom", "inventory.view_uom",
        "user.add_customuser", "user.change_customuser", "user.delete_customuser", "user.view_customuser",
    ],
    GROUP_SERVICE_ADVISOR: [
        # Service advisor / service manager manages customers, vehicles, job cards, invoices, views inventory
        "customer.add_customer", "customer.change_customer", "customer.view_customer",
        "vehicle.add_vehiclemodel", "vehicle.change_vehiclemodel", "vehicle.view_vehiclemodel",
        "vehicle.add_vehiclemake", "vehicle.change_vehiclemake", "vehicle.view_vehiclemake",
        "jobcard.add_jobcard", "jobcard.change_jobcard", "jobcard.view_jobcard",
        "jobcard.add_jobcarditem", "jobcard.change_jobcarditem", "jobcard.view_jobcarditem",
        "invoice.add_invoice", "invoice.change_invoice", "invoice.view_invoice",
        "invoice.add_invoiceitem", "invoice.change_invoiceitem", "invoice.view_invoiceitem",
        "inventory.view_inventory", "inventory.change_inventory",
        "inventory.view_category", "inventory.view_uom",
    ],
    GROUP_INVENTORY_MANAGER: [
        # Inventory / Parts manager has full control of inventory, parts, categories, uom
        "inventory.add_inventory", "inventory.change_inventory", "inventory.delete_inventory", "inventory.view_inventory",
        "inventory.add_category", "inventory.change_category", "inventory.delete_category", "inventory.view_category",
        "inventory.add_uom", "inventory.change_uom", "inventory.delete_uom", "inventory.view_uom",
        "jobcard.view_jobcard", "jobcard.view_jobcarditem",
        "invoice.view_invoice", "invoice.view_invoiceitem",
    ],
    GROUP_BILLING: [
        # Billing / Cashier manages invoices and views customer/vehicle/job card details
        "invoice.add_invoice", "invoice.change_invoice", "invoice.view_invoice",
        "invoice.add_invoiceitem", "invoice.change_invoiceitem", "invoice.view_invoiceitem",
        "customer.add_customer", "customer.view_customer",
        "vehicle.view_vehiclemodel", "vehicle.view_vehiclemake",
        "jobcard.view_jobcard", "jobcard.view_jobcarditem",
        "inventory.view_inventory",
    ],
    GROUP_TECHNICIAN: [
        # Mechanics / technicians view jobcards, add/update parts & labor items, view vehicles & parts
        "jobcard.view_jobcard", "jobcard.change_jobcard",
        "jobcard.add_jobcarditem", "jobcard.change_jobcarditem", "jobcard.view_jobcarditem",
        "vehicle.view_vehiclemodel", "vehicle.view_vehiclemake",
        "inventory.view_inventory",
    ],
}


def setup_default_roles_and_permissions():
    """
    Creates or updates the default GarageFlow user groups and assigns
    their respective permissions. Safe to run multiple times.
    """
    created_groups = []
    for group_name, perm_codenames in DEFAULT_GROUP_PERMISSIONS.items():
        group, created = Group.objects.get_or_create(name=group_name)
        if created:
            created_groups.append(group_name)

        perms_to_add = []
        for perm_str in perm_codenames:
            app_label, codename = perm_str.split(".")
            try:
                perm = Permission.objects.get(content_type__app_label=app_label, codename=codename)
                perms_to_add.append(perm)
            except Permission.DoesNotExist:
                logger.warning(f"Permission {perm_str} not found in database.")

        group.permissions.set(perms_to_add)

    return created_groups

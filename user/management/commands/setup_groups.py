from django.core.management.base import BaseCommand
from user.permissions import setup_default_roles_and_permissions, DEFAULT_GROUP_PERMISSIONS


class Command(BaseCommand):
    help = "Sets up standard GarageFlow groups (roles) and their associated permissions."

    def handle(self, *args, **options):
        self.stdout.write("Setting up standard GarageFlow groups and permissions...")
        setup_default_roles_and_permissions()
        self.stdout.write(self.style.SUCCESS("Successfully configured groups and permissions:"))
        for group_name, perms in DEFAULT_GROUP_PERMISSIONS.items():
            self.stdout.write(f"  - {group_name} ({len(perms)} permissions)")

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.management import call_command
from user.permissions import (
    setup_default_roles_and_permissions,
    GROUP_SERVICE_ADVISOR,
    GROUP_INVENTORY_MANAGER,
    GROUP_BILLING,
    GROUP_TECHNICIAN,
    GROUP_ADMIN,
)
from user.forms import CustomUserCreationForm, CustomUserChangeForm

User = get_user_model()


class UserModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            phone="9876543210",
            password="testpassword123",
            first_name="Raj",
            last_name="Kumar",
        )

    def test_user_creation_and_employee_id(self):
        self.assertEqual(self.user.phone, "9876543210")
        self.assertTrue(self.user.employee_id.startswith("EMP"))
        self.assertEqual(self.user.get_full_name(), "Raj Kumar")
        self.assertTrue(self.user.check_password("testpassword123"))

    def test_phone_validation(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(phone="123", password="testpassword123")

    def test_superuser_creation(self):
        admin = User.objects.create_superuser(
            phone="9999999999",
            password="adminpassword123",
            first_name="Admin",
            last_name="Root",
        )
        self.assertTrue(admin.is_superuser)
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_admin)
        self.assertEqual(admin.primary_role, "Administrator")


class RolePermissionBackendTests(TestCase):
    def setUp(self):
        setup_default_roles_and_permissions()
        self.admin_group = Group.objects.get(name=GROUP_ADMIN)
        self.admin_user = User.objects.create_user(
            phone="9000000001",
            password="password123",
            first_name="Admin",
            last_name="One",
        )
        self.admin_user.groups.add(self.admin_group)

        self.advisor_group = Group.objects.get(name=GROUP_SERVICE_ADVISOR)
        self.staff_user = User.objects.create_user(
            phone="9000000002",
            password="password123",
            first_name="Staff",
            last_name="Two",
            is_staff=True,
        )
        self.staff_user.groups.add(self.advisor_group)

    def test_admin_has_full_permissions(self):
        self.assertTrue(self.admin_user.has_perm("inventory.add_inventory"))
        self.assertTrue(self.admin_user.has_perm("inventory.delete_inventory"))
        self.assertTrue(self.admin_user.has_perm("user.add_customuser"))
        self.assertTrue(self.admin_user.has_perm("user.delete_customuser"))
        self.assertTrue(self.admin_user.has_perm("jobcard.add_jobcard"))

    def test_staff_has_operational_permissions(self):
        self.assertTrue(self.staff_user.has_perm("jobcard.add_jobcard"))
        self.assertTrue(self.staff_user.has_perm("jobcard.change_jobcard"))
        self.assertTrue(self.staff_user.has_perm("customer.add_customer"))
        self.assertTrue(self.staff_user.has_perm("invoice.add_invoice"))
        self.assertTrue(self.staff_user.has_perm("inventory.view_inventory"))

    def test_staff_denied_admin_permissions(self):
        self.assertFalse(self.staff_user.has_perm("user.add_customuser"))
        self.assertFalse(self.staff_user.has_perm("user.delete_customuser"))
        self.assertFalse(self.staff_user.has_perm("inventory.delete_inventory"))
        self.assertFalse(self.staff_user.has_perm("customer.delete_customer"))


class DynamicGroupPermissionTests(TestCase):
    """
    Tests ensuring permissions work dynamically through Django Groups
    (e.g., Service Advisor, Inventory Manager, Cashier, or any custom team group).
    """

    def setUp(self):
        setup_default_roles_and_permissions()
        self.service_advisor_group = Group.objects.get(name=GROUP_SERVICE_ADVISOR)
        self.inventory_manager_group = Group.objects.get(name=GROUP_INVENTORY_MANAGER)

    def test_service_advisor_permissions(self):
        user = User.objects.create_user(
            phone="9111111111",
            password="password123",
            first_name="Service",
            last_name="Advisor",
        )
        user.groups.add(self.service_advisor_group)

        # Permissions granted via group
        self.assertTrue(user.has_perm("jobcard.add_jobcard"))
        self.assertTrue(user.has_perm("jobcard.change_jobcard"))
        self.assertTrue(user.has_perm("customer.add_customer"))
        self.assertTrue(user.has_perm("invoice.add_invoice"))
        self.assertTrue(user.has_perm("inventory.view_inventory"))

        # Disallowed permissions
        self.assertFalse(user.has_perm("inventory.delete_inventory"))
        self.assertFalse(user.has_perm("user.add_customuser"))
        self.assertFalse(user.has_perm("user.delete_customuser"))
        self.assertEqual(user.primary_role, GROUP_SERVICE_ADVISOR)

    def test_inventory_manager_permissions(self):
        user = User.objects.create_user(
            phone="9222222222",
            password="password123",
            first_name="Inventory",
            last_name="Manager",
        )
        user.groups.add(self.inventory_manager_group)

        # Can manage full inventory
        self.assertTrue(user.has_perm("inventory.add_inventory"))
        self.assertTrue(user.has_perm("inventory.change_inventory"))
        self.assertTrue(user.has_perm("inventory.delete_inventory"))
        self.assertTrue(user.has_perm("inventory.add_category"))
        self.assertTrue(user.has_perm("inventory.add_uom"))

        # Cannot add job cards or manage users
        self.assertFalse(user.has_perm("jobcard.add_jobcard"))
        self.assertFalse(user.has_perm("user.add_customuser"))
        self.assertEqual(user.primary_role, GROUP_INVENTORY_MANAGER)

    def test_custom_dynamic_group_creation(self):
        """
        Verify that creating an arbitrary new group (e.g. 'KM Manager') with specific permissions
        works seamlessly without changing code.
        """
        km_group = Group.objects.create(name="KM Manager")
        view_vehicle = Permission.objects.get(
            content_type__app_label="vehicle", codename="view_vehiclemodel"
        )
        view_jobcard = Permission.objects.get(
            content_type__app_label="jobcard", codename="view_jobcard"
        )
        km_group.permissions.set([view_vehicle, view_jobcard])

        km_user = User.objects.create_user(
            phone="9333333333",
            password="password123",
            first_name="Key",
            last_name="Manager",
        )
        km_user.groups.add(km_group)

        self.assertTrue(km_user.has_perm("vehicle.view_vehiclemodel"))
        self.assertTrue(km_user.has_perm("jobcard.view_jobcard"))
        self.assertFalse(km_user.has_perm("inventory.add_inventory"))
        self.assertFalse(km_user.has_perm("jobcard.add_jobcard"))
        self.assertEqual(km_user.primary_role, "KM Manager")

    def test_setup_groups_command(self):
        """Test management command 'setup_groups'."""
        call_command("setup_groups")
        self.assertTrue(Group.objects.filter(name=GROUP_ADMIN).exists())
        self.assertTrue(Group.objects.filter(name=GROUP_SERVICE_ADVISOR).exists())
        self.assertTrue(Group.objects.filter(name=GROUP_INVENTORY_MANAGER).exists())
        self.assertTrue(Group.objects.filter(name=GROUP_BILLING).exists())
        self.assertTrue(Group.objects.filter(name=GROUP_TECHNICIAN).exists())


class UserFormGroupTests(TestCase):
    def setUp(self):
        setup_default_roles_and_permissions()
        self.advisor_group = Group.objects.get(name=GROUP_SERVICE_ADVISOR)

    def test_user_creation_with_groups(self):
        form_data = {
            "phone": "9444444444",
            "first_name": "New",
            "last_name": "User",
            "password1": "SecurePass123",
            "password2": "SecurePass123",
            "groups": [self.advisor_group.pk],
            "is_active": True,
            "is_staff": False,
        }
        form = CustomUserCreationForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()
        self.assertTrue(user.groups.filter(pk=self.advisor_group.pk).exists())
        self.assertTrue(user.has_perm("jobcard.add_jobcard"))


class NavigationAndButtonPermissionTests(TestCase):
    """
    Tests ensuring navbar links and action buttons are properly gated
    based on user permissions across different roles.
    """

    def setUp(self):
        setup_default_roles_and_permissions()
        self.tech_group = Group.objects.get(name=GROUP_TECHNICIAN)
        self.billing_group = Group.objects.get(name=GROUP_BILLING)
        self.admin_group = Group.objects.get(name=GROUP_ADMIN)

        self.tech_user = User.objects.create_user(
            phone="9555555551",
            password="password123",
            first_name="Tech",
            last_name="User",
        )
        self.tech_user.groups.add(self.tech_group)

        self.cashier_user = User.objects.create_user(
            phone="9555555552",
            password="password123",
            first_name="Cashier",
            last_name="User",
        )
        self.cashier_user.groups.add(self.billing_group)

        self.admin_user = User.objects.create_superuser(
            phone="9555555553",
            password="password123",
            first_name="Super",
            last_name="Admin",
        )

    def test_technician_navbar_restrictions(self):
        """Technician should only see authorized nav items and be redirected from dashboard."""
        from django.urls import reverse
        self.client.login(phone="9555555551", password="password123")
        response = self.client.get("/", follow=True)
        # Non-admin technician redirected to jobcards
        self.assertRedirects(response, reverse("jobcard:list"))
        self.assertEqual(response.status_code, 200)

        # Dashboard is hidden from navbar
        self.assertNotContains(response, 'id="wrap-dashboard"')

        # Authorized items
        self.assertContains(response, 'id="wrap-jobcards"')
        self.assertContains(response, 'id="wrap-vehicles"')
        self.assertContains(response, 'id="wrap-inventory"')

        # Hidden items
        self.assertNotContains(response, 'id="wrap-customers"')
        self.assertNotContains(response, 'id="wrap-invoices"')
        self.assertNotContains(response, 'id="wrap-users"')

        # Sub-link permissions (Technician cannot add job cards or vehicle models)
        self.assertNotContains(response, reverse("jobcard:add"))
        self.assertNotContains(response, reverse("vehicle:add"))
        self.assertNotContains(response, reverse("inventory:add"))

    def test_cashier_navbar_and_invoice_add_button(self):
        """Cashier should see Invoices (with Add link and Add Invoice button) and no dashboard."""
        from django.urls import reverse
        self.client.login(phone="9555555552", password="password123")

        # Navbar checks via landing page
        response = self.client.get("/", follow=True)
        self.assertRedirects(response, reverse("invoice:list"))
        self.assertEqual(response.status_code, 200)

        self.assertNotContains(response, 'id="wrap-dashboard"')
        self.assertContains(response, 'id="wrap-invoices"')
        self.assertContains(response, reverse("invoice:add"))
        self.assertNotContains(response, 'id="wrap-users"')

        # Invoice list page check
        inv_response = self.client.get(reverse("invoice:list"))
        self.assertEqual(inv_response.status_code, 200)
        self.assertContains(inv_response, "Add Invoice")
        self.assertContains(inv_response, reverse("invoice:add"))

    def test_admin_sees_all_navbar_items(self):
        """Administrator / superuser sees all navbar sections and links."""
        from django.urls import reverse
        self.client.login(phone="9555555553", password="password123")
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, 'id="wrap-dashboard"')
        self.assertContains(response, 'id="wrap-jobcards"')
        self.assertContains(response, 'id="wrap-customers"')
        self.assertContains(response, 'id="wrap-vehicles"')
        self.assertContains(response, 'id="wrap-inventory"')
        self.assertContains(response, 'id="wrap-invoices"')
        self.assertContains(response, 'id="wrap-users"')

        self.assertContains(response, reverse("jobcard:add"))
        self.assertContains(response, reverse("customer:add"))
        self.assertContains(response, reverse("vehicle:add"))
        self.assertContains(response, reverse("inventory:add"))
        self.assertContains(response, reverse("invoice:add"))
        self.assertContains(response, reverse("user:add"))

    def test_custom_user_with_view_dashboard_permission(self):
        """User with user.view_dashboard permission can see and access dashboard."""
        from django.contrib.auth.models import Permission
        perm = Permission.objects.get(codename="view_dashboard")
        dash_user = User.objects.create_user(
            phone="9555555554",
            password="password123",
            first_name="Dash",
            last_name="User",
        )
        dash_user.user_permissions.add(perm)

        self.client.login(phone="9555555554", password="password123")
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="wrap-dashboard"')

    def test_jobcard_detail_button_permissions(self):
        """Verify Submit button visibility on Job Card detail page based on permissions."""
        from customer.models import Customer
        from jobcard.models import JobCard
        from django.urls import reverse

        customer = Customer.objects.create(name="Test Customer", phone="9888888888")
        jobcard = JobCard.objects.create(
            customer=customer,
            vehicle_number="KA01AB1234",
            created_by=self.admin_user,
        )

        detail_url = reverse("jobcard:detail", kwargs={"pk": jobcard.pk})

        # 1. Cashier lacks jobcard.change_jobcard -> cannot see Submit button or search parts
        self.client.login(phone="9555555552", password="password123")
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'action="/jobcards/1/submit/"')
        self.assertNotContains(response, 'id="jc-inv-search"')

        # 2. Technician has jobcard.change_jobcard and add_jobcarditem -> can see Submit button and search
        self.client.login(phone="9555555551", password="password123")
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'action="{reverse("jobcard:submit", kwargs={"pk": jobcard.pk})}"')
        self.assertContains(response, 'id="jc-inv-search"')



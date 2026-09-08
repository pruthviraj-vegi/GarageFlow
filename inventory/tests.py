import base64
from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from inventory.models import Inventory, Category, UOM, InventoryLog
from inventory.services import InventoryService
from customer.models import Customer
from vehicle.models import VehicleMake, VehicleModel
from jobcard.models import JobCard, JobCardItem

User = get_user_model()


class InventoryModelAndServiceTests(TestCase):
    def setUp(self):
        self.cat = Category.objects.create(name="Filters")
        self.uom = UOM.objects.create(name="Pieces")
        self.inv = Inventory.objects.create(
            name="Air Filter",
            category=self.cat,
            uom=self.uom,
            cost_price=Decimal("200.00"),
            selling_price=Decimal("350.00"),
            quantity=Decimal("20.00"),
            low_stock=Decimal("5.00"),
        )

    def test_barcode_generation(self):
        self.assertTrue(bool(self.inv.barcode))
        self.assertTrue(self.inv.barcode.endswith("3"))
        self.assertEqual(self.inv.barcode, f"{self.inv.id:06d}3")

    def test_custom_barcode_preserved(self):
        item = Inventory.objects.create(
            name="Oil Filter",
            category=self.cat,
            uom=self.uom,
            cost_price=Decimal("150.00"),
            selling_price=Decimal("250.00"),
            quantity=Decimal("5.00"),
            barcode="CUSTOM-BARCODE-999",
        )
        self.assertEqual(item.barcode, "CUSTOM-BARCODE-999")

    def test_record_purchase(self):
        initial_qty = self.inv.quantity
        log = InventoryService.record_purchase(
            inventory=self.inv,
            quantity=Decimal("10.00"),
            reference_number="PO-101",
        )
        self.assertEqual(log.quantity, Decimal("10.00"))
        self.inv.refresh_from_db()
        self.assertEqual(self.inv.quantity, initial_qty + Decimal("10.00"))

    def test_record_sale(self):
        initial_qty = self.inv.quantity
        log = InventoryService.record_sale(
            inventory=self.inv,
            quantity=Decimal("5.00"),
            reference_number="INV-202",
        )
        self.assertEqual(log.quantity, Decimal("-5.00"))
        self.inv.refresh_from_db()
        self.assertEqual(self.inv.quantity, initial_qty - Decimal("5.00"))

    def test_negative_stock_validation(self):
        # When allow_negative is False, raising ValidationError on insufficient stock
        with self.assertRaises(ValidationError):
            InventoryService.record_sale(
                inventory=self.inv,
                quantity=Decimal("50.00"),
                allow_negative=False,
            )

    def test_reserved_quantity_includes_pending_and_in_progress(self):
        c = Customer.objects.create(name="Deepak", phone="9111111111")
        make = VehicleMake.objects.create(name="Tata")
        vm = VehicleModel.objects.create(make=make, model_name="Nexon", fuel_type="petrol", transmission="manual")

        # Job card 1: pending with 2 units
        jc_pending = JobCard.objects.create(customer=c, vehicle_model=vm, vehicle_number="DL-01-AA-1111", status=JobCard.Status.PENDING)
        JobCardItem.objects.create(job_card=jc_pending, inventory=self.inv, quantity=Decimal("2.00"), unit_price=self.inv.selling_price)

        # Job card 2: in_progress with 3 units
        jc_progress = JobCard.objects.create(customer=c, vehicle_model=vm, vehicle_number="DL-01-AA-2222", status=JobCard.Status.IN_PROGRESS)
        JobCardItem.objects.create(job_card=jc_progress, inventory=self.inv, quantity=Decimal("3.00"), unit_price=self.inv.selling_price)

        # Total reserved should be 2 + 3 = 5
        self.assertEqual(self.inv.reserved_quantity, Decimal("5.00"))
        # Available quantity should be 20 - 5 = 15
        self.assertEqual(self.inv.available_quantity, Decimal("15.00"))

    def test_inventory_print_barcode_view(self):
        user = User.objects.create_superuser(
            phone="9876543210", password="password123", first_name="Admin", last_name="User"
        )
        client = Client()
        client.login(username="9876543210", password="password123")

        url = reverse("inventory:print_barcode", kwargs={"pk": self.inv.pk})
        response = client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.inv.barcode)
        self.assertContains(response, "Air Filter")
        self.assertContains(response, "data:image/svg+xml;base64,")
        # Ensure the text/number below the barcode bars is removed from the SVG
        svg_content = base64.b64decode(response.context["barcode_svg"]).decode("utf-8")
        self.assertNotIn("<text", svg_content)

    def test_inventory_print_barcode_custom_count(self):
        user = User.objects.create_superuser(
            phone="9876543211", password="password123", first_name="Staff", last_name="User"
        )
        client = Client()
        client.login(username="9876543211", password="password123")

        url = reverse("inventory:print_barcode", kwargs={"pk": self.inv.pk}) + "?count=3"
        response = client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["print_count"], 3)

    def test_inventory_print_barcode_unauthenticated(self):
        client = Client()
        url = reverse("inventory:print_barcode", kwargs={"pk": self.inv.pk})
        response = client.get(url)
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_inventory_form_category_and_uom_initial_default(self):
        from inventory.forms import InventoryForm

        # For a new item, category and uom should default to first Category and UOM
        form = InventoryForm()
        self.assertEqual(form.initial.get("category"), self.cat.pk)
        self.assertEqual(form.initial.get("uom"), self.uom.pk)

        # Explicit initial should be respected
        cat2 = Category.objects.create(name="Brakes")
        form_explicit = InventoryForm(initial={"category": cat2.pk})
        self.assertEqual(form_explicit.initial.get("category"), cat2.pk)
        self.assertEqual(form_explicit.initial.get("uom"), self.uom.pk)

    def test_inventory_create_view_initial_values(self):
        user = User.objects.create_superuser(
            phone="9876543212", password="password123", first_name="Admin", last_name="User"
        )
        client = Client()
        client.login(username="9876543212", password="password123")

        url = reverse("inventory:add")
        response = client.get(url)
        self.assertEqual(response.status_code, 200)
        # Check that form in context has initial category and uom
        form = response.context["form"]
        self.assertEqual(form.initial.get("category"), self.cat.pk)
        self.assertEqual(form.initial.get("uom"), self.uom.pk)


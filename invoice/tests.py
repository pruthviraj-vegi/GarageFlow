from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from customer.models import Customer
from vehicle.models import VehicleMake, VehicleModel
from inventory.models import Inventory
from jobcard.models import JobCard, JobCardItem
from invoice.models import Invoice, InvoiceItem

User = get_user_model()


class InvoiceAndJobCardSubmitTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            phone="9876543210", password="password123", first_name="Test", last_name="Staff"
        )
        self.client = Client()
        self.client.login(username="9876543210", password="password123")

        self.customer = Customer.objects.create(name="Rohit Sharma", phone="9988112233")
        self.make = VehicleMake.objects.create(name="Toyota")
        self.model = VehicleModel.objects.create(
            make=self.make, model_name="Innova", fuel_type="diesel", transmission="manual"
        )
        self.inv = Inventory.objects.create(
            name="Brake Pad Front",
            cost_price=Decimal("800.00"),
            selling_price=Decimal("1400.00"),
            quantity=Decimal("10.00"),
            barcode="BPTOY01",
        )
        self.jc = JobCard.objects.create(
            customer=self.customer,
            vehicle_model=self.model,
            vehicle_number="MH-02-CD-5678",
            status=JobCard.Status.PENDING,
        )
        self.item = JobCardItem.objects.create(
            job_card=self.jc,
            inventory=self.inv,
            quantity=Decimal("2.00"),
            unit_price=self.inv.selling_price,
        )

    def test_invoice_id_generation(self):
        inv = Invoice.objects.create(customer=self.customer, total_amount=Decimal("2800.00"))
        self.assertTrue(inv.invoice_number.startswith("INV"))

    def test_jobcard_submit_creates_invoice_and_deducts_inventory(self):
        url = reverse("jobcard:submit", kwargs={"pk": self.jc.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)  # Redirect to detail

        self.jc.refresh_from_db()
        self.assertEqual(self.jc.status, JobCard.Status.COMPLETED)
        self.assertIsNotNone(self.jc.completed_at)

        # Invoice should exist
        invoice = Invoice.objects.filter(job_card=self.jc).first()
        self.assertIsNotNone(invoice)
        self.assertEqual(invoice.total_amount, Decimal("2800.00"))
        self.assertRedirects(response, reverse("invoice:detail", kwargs={"pk": invoice.pk}))

        # Invoice item should exist
        invoice_item = InvoiceItem.objects.filter(invoice=invoice).first()
        self.assertIsNotNone(invoice_item)
        self.assertEqual(invoice_item.quantity, Decimal("2.00"))

        # Inventory quantity should have decreased from 10 to 8
        self.inv.refresh_from_db()
        self.assertEqual(self.inv.quantity, Decimal("8.00"))

    def test_invoice_print_58mm_view(self):
        invoice = Invoice.objects.create(
            customer=self.customer,
            job_card=self.jc,
            total_amount=Decimal("2800.00"),
            notes="Test invoice note",
        )
        InvoiceItem.objects.create(
            invoice=invoice,
            inventory=self.inv,
            description="Brake Pad Front",
            quantity=Decimal("2.00"),
            unit_price=Decimal("1400.00"),
        )

        # Test both named URLs
        url_58mm = reverse("invoice:print_58mm", kwargs={"pk": invoice.pk})
        url_print = reverse("invoice:print", kwargs={"pk": invoice.pk})

        res_58mm = self.client.get(url_58mm)
        self.assertEqual(res_58mm.status_code, 200)
        self.assertContains(res_58mm, "58mm.css")
        self.assertContains(res_58mm, invoice.invoice_number)
        self.assertContains(res_58mm, "Rohit Sharma")
        self.assertContains(res_58mm, "MH-02-CD-5678")
        self.assertContains(res_58mm, "Brake Pad Front")
        self.assertContains(res_58mm, "2,800.00")
        self.assertContains(res_58mm, "Test invoice note")

        res_print = self.client.get(url_print)
        self.assertEqual(res_print.status_code, 200)

    def test_invoice_print_58mm_unauthenticated(self):
        invoice = Invoice.objects.create(
            customer=self.customer,
            total_amount=Decimal("500.00"),
        )
        self.client.logout()
        url = reverse("invoice:print_58mm", kwargs={"pk": invoice.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)  # Redirect to login


from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from customer.models import Customer
from vehicle.models import VehicleMake, VehicleModel
from inventory.models import Inventory
from jobcard.models import JobCard, JobCardItem

User = get_user_model()


class JobCardTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            phone="9876543210", password="password123", first_name="Test", last_name="Staff"
        )
        self.client = Client()
        self.client.login(username="9876543210", password="password123")

        self.customer = Customer.objects.create(name="Rahul Roy", phone="9988776655")
        self.make = VehicleMake.objects.create(name="Honda")
        self.model = VehicleModel.objects.create(
            make=self.make, model_name="City", fuel_type="petrol", transmission="manual"
        )
        self.inv = Inventory.objects.create(
            name="Engine Oil 5W30",
            cost_price=Decimal("1500.00"),
            selling_price=Decimal("2200.00"),
            quantity=Decimal("50.00"),
            barcode="OIL5W30",
        )
        self.jc = JobCard.objects.create(
            customer=self.customer,
            vehicle_model=self.model,
            vehicle_number="KA-05-MM-1234",
            status=JobCard.Status.PENDING,
        )

    def test_job_card_id_generation(self):
        self.assertTrue(self.jc.job_card_number.startswith("JC"))

    def test_add_item_ajax(self):
        url = reverse("jobcard:api_add_item", kwargs={"pk": self.jc.pk})
        response = self.client.post(url, {"barcode": "OIL5W30"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(self.jc.job_card_items.count(), 1)
        self.assertEqual(self.jc.get_total_price, Decimal("2200.00"))

    def test_update_item_qty_ajax(self):
        item = JobCardItem.objects.create(
            job_card=self.jc, inventory=self.inv, quantity=Decimal("1.00"), unit_price=self.inv.selling_price
        )
        url = reverse("jobcard:api_update_item_qty", kwargs={"pk": self.jc.pk, "item_pk": item.pk})
        response = self.client.post(url, {"quantity": "3.00"})
        self.assertEqual(response.status_code, 200)
        item.refresh_from_db()
        self.assertEqual(item.quantity, Decimal("3.00"))

    def test_update_item_qty_zero_or_negative_rejected(self):
        item = JobCardItem.objects.create(
            job_card=self.jc, inventory=self.inv, quantity=Decimal("1.00"), unit_price=self.inv.selling_price
        )
        url = reverse("jobcard:api_update_item_qty", kwargs={"pk": self.jc.pk, "item_pk": item.pk})
        response = self.client.post(url, {"quantity": "0"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())

    def test_cannot_mutate_completed_jobcard(self):
        self.jc.status = JobCard.Status.COMPLETED
        self.jc.save()

        # Try to add item
        add_url = reverse("jobcard:api_add_item", kwargs={"pk": self.jc.pk})
        res = self.client.post(add_url, {"barcode": "OIL5W30"})
        self.assertEqual(res.status_code, 400)
        self.assertIn("error", res.json())

    def test_cannot_mutate_cancelled_jobcard(self):
        self.jc.status = JobCard.Status.CANCELLED
        self.jc.save()

        add_url = reverse("jobcard:api_add_item", kwargs={"pk": self.jc.pk})
        res = self.client.post(add_url, {"barcode": "OIL5W30"})
        self.assertEqual(res.status_code, 400)
        self.assertIn("error", res.json())

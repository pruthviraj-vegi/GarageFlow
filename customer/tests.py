from django.test import TestCase
from django.core.exceptions import ValidationError
from customer.models import Customer


class CustomerModelTests(TestCase):
    def test_customer_creation_and_id_generation(self):
        c1 = Customer.objects.create(name="Anand Sharma", phone="9876543211")
        self.assertTrue(c1.customer_id.startswith("CUST"))
        self.assertEqual(str(c1), "Anand Sharma - 9876543211")

        c2 = Customer.objects.create(name="Priya Patel", phone="9876543212")
        self.assertTrue(c2.customer_id.startswith("CUST"))
        self.assertNotEqual(c1.customer_id, c2.customer_id)

    def test_soft_delete(self):
        c = Customer.objects.create(name="Ravi Kumar", phone="9876543213")
        pk = c.pk
        c.delete()

        # Regular objects manager excludes soft-deleted records
        self.assertFalse(Customer.objects.filter(pk=pk).exists())
        # all_objects manager retains it
        self.assertTrue(Customer.all_objects.filter(pk=pk).exists())

        # Restore
        c.restore()
        self.assertTrue(Customer.objects.filter(pk=pk).exists())

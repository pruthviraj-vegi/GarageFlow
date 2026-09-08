from django.test import TestCase
from django.db.utils import IntegrityError
from vehicle.models import VehicleMake, VehicleModel


class VehicleModelTests(TestCase):
    def setUp(self):
        self.make = VehicleMake.objects.create(name="Hyundai")

    def test_vehicle_make_creation(self):
        self.assertEqual(str(self.make), "Hyundai")

    def test_vehicle_model_creation(self):
        vm = VehicleModel.objects.create(
            make=self.make,
            model_name="Creta",
            fuel_type=VehicleModel.FuelTypeChoices.DIESEL,
            transmission=VehicleModel.TransmissionChoices.AUTOMATIC,
        )
        self.assertEqual(vm.display_name, "Hyundai Creta")
        self.assertIn("diesel", str(vm))

    def test_unique_constraint(self):
        VehicleModel.objects.create(
            make=self.make,
            model_name="Verna",
            fuel_type=VehicleModel.FuelTypeChoices.PETROL,
            transmission=VehicleModel.TransmissionChoices.MANUAL,
        )
        with self.assertRaises(IntegrityError):
            VehicleModel.objects.create(
                make=self.make,
                model_name="Verna",
                fuel_type=VehicleModel.FuelTypeChoices.PETROL,
                transmission=VehicleModel.TransmissionChoices.MANUAL,
            )

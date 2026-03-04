from django.urls import path
from . import suggestions


app_name = "suggestions"

urlpatterns = [
    path("inventory/", suggestions.inventory_all_suggestions, name="inventory_all"),
    path("vehicle/", suggestions.vehicle_all_suggestions, name="vehicle_all"),
    path("customer/", suggestions.customer_all_suggestions, name="customer_all"),
    path("jobcard/", suggestions.jobcard_all_suggestions, name="jobcard_all"),
    path("invoice/", suggestions.invoice_all_suggestions, name="invoice_all"),
]

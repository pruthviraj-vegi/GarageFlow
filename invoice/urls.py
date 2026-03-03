from django.urls import path
from . import views

app_name = "invoice"

urlpatterns = [
    path("", views.invoice_list, name="list"),
    path("fetch/", views.fetch_invoices, name="fetch"),
    path("add/", views.InvoiceCreateView.as_view(), name="add"),
    path("<int:pk>/", views.InvoiceDetailView.as_view(), name="detail"),
    path("<int:pk>/edit/", views.InvoiceUpdateView.as_view(), name="edit"),
    path("<int:pk>/delete/", views.invoice_delete, name="delete"),
]

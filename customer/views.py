"""Views for the customer management module."""

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.db.models import Q
from django.http import JsonResponse
from django.views.generic import CreateView, UpdateView
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from base.utility import render_paginated_response, table_sorting
from .models import Customer
from .forms import CustomerForm


@login_required
def home(request):
    """Customer management main page - initial load only."""
    # For initial page load, just render the template with empty data
    customers_count = Customer.objects.count()
    return render(
        request,
        "customer/main.html",
        {"title": "Customers", "customers_count": customers_count},
    )


def get_data(request):
    """Return a filtered and sorted customer queryset based on request params."""
    # Get search and filter parameters
    search_query = request.GET.get("q", "")

    # Apply search filter
    queryset = Customer.objects.all()
    if search_query:
        queryset = queryset.filter(
            Q(name__icontains=search_query)
            | Q(phone__icontains=search_query)
            | Q(customer_id__icontains=search_query)
            | Q(address__icontains=search_query)
        )

    # Apply sorting (Multi-column support)
    valid_sorts = table_sorting(
        request,
        valid_sorts=["name", "phone", "created_at", "customer_id"],
        default_sort="-created_at",
    )

    queryset = queryset.order_by(*valid_sorts)

    return queryset


@login_required
def fetch_customers(request):
    """AJAX endpoint to fetch customers with search, filter, and pagination."""
    customers = get_data(request)

    # Render and return paginated response using utility
    return render_paginated_response(
        request,
        customers,
        "customer/fetch.html",
        per_page=10,
    )


class CustomerCreateView(
    LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, CreateView
):
    """View for creating a new customer."""

    model = Customer
    form_class = CustomerForm
    template_name = "customer/form.html"
    permission_required = "customer.add_customer"
    success_url = reverse_lazy("customer:list")
    extra_context = {"title": "Add New Customer"}

    def get_success_message(self, cleaned_data):
        return f"Customer {self.object.name} created successfully."

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)


class CustomerUpdateView(
    LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, UpdateView
):
    """View for updating an existing customer."""

    model = Customer
    form_class = CustomerForm
    template_name = "customer/form.html"
    permission_required = "customer.change_customer"
    success_url = reverse_lazy("customer:list")
    extra_context = {"title": "Edit Customer", "is_edit": True}

    def get_success_message(self, cleaned_data):
        return f"Customer {self.object.name} updated successfully."


@login_required
@permission_required("customer.add_customer", raise_exception=True)
def customer_create_ajax(request):
    """AJAX endpoint to create a customer from a modal on any page."""
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    form = CustomerForm(request.POST)
    if form.is_valid():
        customer = form.save(commit=False)
        customer.created_by = request.user
        customer.save()
        return JsonResponse(
            {
                "success": True,
                "customer": {
                    "id": customer.pk,
                    "name": customer.name,
                    "phone": customer.phone,
                    "display": str(customer),
                },
            }
        )

    # Return field-level errors
    errors = {field: errs[0] for field, errs in form.errors.items()}
    return JsonResponse({"success": False, "errors": errors}, status=400)


@login_required
@permission_required("customer.delete_customer", raise_exception=True)
def customer_delete(request, pk):
    """Delete a customer"""
    customer = get_object_or_404(Customer, pk=pk)
    if request.method == "POST":
        customer.delete()
        messages.success(request, "Customer deleted successfully.")
        return redirect("customer:list")

    return render(request, "customer/delete.html", {"object": customer})

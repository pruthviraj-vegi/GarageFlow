from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView, DetailView
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.db.models import Q
from base.utility import render_paginated_response, table_sorting
from .models import Invoice
from .forms import InvoiceForm


@login_required
def invoice_list(request):
    """List all invoices (initial load only)"""
    invoices_count = Invoice.objects.count()
    return render(
        request,
        "invoice/main.html",
        {
            "title": "Invoices",
            "invoices_count": invoices_count,
            "search_query": request.GET.get("q", ""),
        },
    )


def get_data(request):
    """Return a filtered and sorted invoice queryset based on request params."""
    search_query = request.GET.get("q", "")

    queryset = Invoice.objects.all().select_related("customer", "job_card")

    if search_query:
        queryset = queryset.filter(
            Q(invoice_number__icontains=search_query)
            | Q(customer__name__icontains=search_query)
            | Q(customer__phone__icontains=search_query)
            | Q(job_card__job_card_number__icontains=search_query)
        )

    valid_sorts = table_sorting(
        request,
        valid_sorts=[
            "invoice_number",
            "customer__name",
            "job_card__job_card_number",
            "total_amount",
            "created_at",
        ],
        default_sort="-created_at",
    )

    queryset = queryset.order_by(*valid_sorts)
    return queryset


@login_required
def fetch_invoices(request):
    """AJAX endpoint to fetch invoices with search, filter, and pagination."""
    items = get_data(request)

    return render_paginated_response(
        request,
        items,
        "invoice/fetch.html",
        per_page=10,
    )


class InvoiceCreateView(
    LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, CreateView
):
    model = Invoice
    form_class = InvoiceForm
    template_name = "invoice/form.html"
    permission_required = "invoice.add_invoice"
    success_url = reverse_lazy("invoice:list")
    extra_context = {"title": "Create Invoice"}

    def get_success_message(self, cleaned_data):
        return f"Invoice {self.object.invoice_number} created successfully."

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)


class InvoiceUpdateView(
    LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, UpdateView
):
    model = Invoice
    form_class = InvoiceForm
    template_name = "invoice/form.html"
    permission_required = "invoice.change_invoice"
    success_url = reverse_lazy("invoice:list")
    extra_context = {"title": "Edit Invoice", "is_edit": True}

    def get_success_message(self, cleaned_data):
        return f"Invoice {self.object.invoice_number} updated successfully."


@login_required
@permission_required("invoice.delete_invoice", raise_exception=True)
def invoice_delete(request, pk):
    """Delete an invoice"""
    invoice = get_object_or_404(Invoice, pk=pk)
    if request.method == "POST":
        invoice.delete()
        messages.success(request, "Invoice deleted successfully.")
        return redirect("invoice:list")

    return render(request, "invoice/delete.html", {"object": invoice})


class InvoiceDetailView(LoginRequiredMixin, DetailView):
    model = Invoice
    template_name = "invoice/detail.html"
    context_object_name = "invoice"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = f"Invoice {self.object.invoice_number}"
        return context

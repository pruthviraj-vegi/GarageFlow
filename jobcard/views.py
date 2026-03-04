"""Views for handling Job Cards and Job Card Items."""

from decimal import Decimal, InvalidOperation

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from base.utility import render_paginated_response, table_sorting
from inventory.models import Inventory
from inventory.services import InventoryService
from invoice.models import Invoice, InvoiceItem
from .forms import JobCardForm
from .models import JobCard, JobCardItem

# ============================================================================
# JOB CARD LIST VIEW
# ============================================================================


@login_required
def jobcard_list(request):
    """List all job cards (initial load only)"""
    jobcards_count = JobCard.objects.count()
    return render(
        request,
        "jobcard/main.html",
        {
            "title": "Job Cards",
            "jobcards_count": jobcards_count,
            "search_query": request.GET.get("q", ""),
            "current_status": request.GET.get("status", JobCard.Status.PENDING),
            "statuses": JobCard.Status.choices,
        },
    )


def get_data(request):
    """Return a filtered and sorted job card queryset based on request params."""
    search_query = request.GET.get("q", "")
    status_filter = request.GET.get("status", JobCard.Status.PENDING)

    queryset = JobCard.objects.all().select_related("customer", "vehicle_model")

    if search_query:
        queryset = queryset.filter(
            Q(job_card_number__icontains=search_query)
            | Q(customer__name__icontains=search_query)
            | Q(vehicle_number__icontains=search_query)
            | Q(vehicle_model__model_name__icontains=search_query)
            | Q(vehicle_model__make__name__icontains=search_query)
        )

    if status_filter:
        queryset = queryset.filter(status=status_filter)

    valid_sorts = table_sorting(
        request,
        valid_sorts=[
            "job_card_number",
            "customer__name",
            "vehicle_number",
            "odometer_reading",
            "status",
            "created_at",
        ],
        default_sort="-created_at",
    )

    queryset = queryset.order_by(*valid_sorts)
    return queryset


@login_required
def fetch_jobcards(request):
    """AJAX endpoint to fetch job cards with search, filter, and pagination."""
    items = get_data(request)

    return render_paginated_response(
        request,
        items,
        "jobcard/fetch.html",
        per_page=10,
    )


class JobCardCreateView(
    LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, CreateView
):
    """View to handle the creation of a new job card."""

    model = JobCard
    form_class = JobCardForm
    template_name = "jobcard/form.html"
    permission_required = "jobcard.add_jobcard"
    extra_context = {"title": "Create Job Card"}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if "customer_form" not in context:
            from customer.forms import CustomerForm

            context["customer_form"] = CustomerForm(prefix="modal-cust")

        if "vehicle_form" not in context:
            from vehicle.forms import VehicleModelForm

            context["vehicle_form"] = VehicleModelForm(prefix="modal-veh")

        return context

    def get_success_url(self):
        return reverse_lazy("jobcard:detail", kwargs={"pk": self.object.pk})

    def get_success_message(self, cleaned_data):
        return f"Job Card {self.object.job_card_number} created successfully."

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.status = JobCard.Status.PENDING
        return super().form_valid(form)

    def form_invalid(self, form):
        print("JOB CARD FORM ERRORS:", form.errors)
        return super().form_invalid(form)


class JobCardUpdateView(
    LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, UpdateView
):
    """View to handle editing an existing job card."""

    model = JobCard
    form_class = JobCardForm
    template_name = "jobcard/form.html"
    permission_required = "jobcard.change_jobcard"
    success_url = reverse_lazy("jobcard:list")
    extra_context = {"title": "Edit Job Card", "is_edit": True}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if "customer_form" not in context:
            from customer.forms import CustomerForm

            context["customer_form"] = CustomerForm(prefix="modal-cust")

        if "vehicle_form" not in context:
            from vehicle.forms import VehicleModelForm

            context["vehicle_form"] = VehicleModelForm(prefix="modal-veh")

        return context

    def get_success_message(self, cleaned_data):
        return f"Job Card {self.object.job_card_number} updated successfully."


@login_required
def jobcard_detail(request, pk):
    """Render the job card detail page — sidebar is server-rendered, items loaded via API"""
    jobcard = get_object_or_404(
        JobCard.objects.select_related("customer", "vehicle_model", "created_by"), pk=pk
    )
    return render(
        request,
        "jobcard/detail.html",
        {
            "title": f"Job Card {jobcard.job_card_number}",
            "jobcard_pk": pk,
            "jobcard": jobcard,
        },
    )


@login_required
@permission_required("jobcard.change_jobcard", raise_exception=True)
def jobcard_submit(request, pk):
    """Submit a job card, create an invoice, and mark it as completed."""
    if request.method != "POST":
        messages.error(request, "Invalid request method.")
        return redirect("jobcard:detail", pk=pk)

    jobcard = get_object_or_404(JobCard, pk=pk)

    if jobcard.status == JobCard.Status.COMPLETED:
        messages.error(request, "Job Card is already completed.")
        return redirect("jobcard:detail", pk=pk)

    if not jobcard.job_card_items.exists():
        messages.error(request, "Cannot submit a Job Card with no items.")
        return redirect("jobcard:detail", pk=pk)

    with transaction.atomic():
        # Create Invoice
        invoice = Invoice.objects.create(
            customer=jobcard.customer,
            job_card=jobcard,
            created_by=request.user,
            total_amount=jobcard.get_total_price,
            notes=f"Generated from Job Card {jobcard.job_card_number}",
        )

        # Create Invoice Items and Record Sales in Inventory Log
        for item in jobcard.job_card_items.all():
            # pylint: disable=no-member
            invoice_item = InvoiceItem.objects.create(
                invoice=invoice,
                inventory=item.inventory,
                description=item.inventory.name,
                quantity=item.quantity,
                unit_price=item.unit_price,
            )

            # Record sale in inventory
            InventoryService.record_sale(
                inventory=item.inventory,
                quantity=item.quantity,
                invoice_item=invoice_item,
                reference_number=invoice.invoice_number,
                notes=f"Sold via Job Card {jobcard.job_card_number}",
                user=request.user,
            )

        # Change Status
        jobcard.status = JobCard.Status.COMPLETED
        jobcard.save()

    messages.success(
        request,
        f"Job Card {jobcard.job_card_number} submitted "
        f"and Invoice {invoice.invoice_number} created successfully.",
    )
    return redirect("jobcard:detail", pk=pk)


@login_required
def jobcard_api_detail(_request, pk):
    """JSON API endpoint — returns only items data for the table"""
    jobcard = get_object_or_404(JobCard, pk=pk)
    items = jobcard.job_card_items.select_related("inventory")

    items_data = []
    grand_total = 0
    for item in items:
        line_total = float(item.total_price)
        grand_total += line_total
        items_data.append(
            {
                "id": item.id,
                "inventory_name": item.inventory.name,
                "barcode": item.inventory.barcode,
                "part_number": item.inventory.part_number,
                "quantity": str(item.quantity),
                "unit_price": str(item.unit_price),
                "total_price": f"{line_total:.2f}",
            }
        )

    return JsonResponse(
        {
            "items": items_data,
            "grand_total": f"{grand_total:.2f}",
        }
    )


@login_required
@permission_required("jobcard.delete_jobcard", raise_exception=True)
def jobcard_delete(request, pk):
    """Delete a job card"""
    jobcard = get_object_or_404(JobCard, pk=pk)
    if request.method == "POST":
        jobcard.delete()
        messages.success(request, "Job Card deleted successfully.")
        return redirect("jobcard:list")

    return render(request, "jobcard/delete.html", {"object": jobcard})


@login_required
def jobcard_add_item(request, pk):
    """Add an inventory item to a job card by barcode (AJAX POST, no reload)"""
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    jobcard = get_object_or_404(JobCard, pk=pk)
    barcode = request.POST.get("barcode", "").strip()

    if not barcode:
        return JsonResponse({"error": "Barcode is required."}, status=400)

    # Look up inventory by barcode
    try:
        inventory = Inventory.objects.get(barcode=barcode)
    except ObjectDoesNotExist:
        return JsonResponse(
            {"error": f"No item found with barcode '{barcode}'."}, status=404
        )

    # Create or increment
    # pylint: disable=no-member
    item, created = JobCardItem.objects.get_or_create(
        job_card=jobcard,
        inventory=inventory,
        defaults={
            "quantity": Decimal("1"),
            "unit_price": inventory.selling_price,
        },
    )

    if not created:
        item.quantity += Decimal("1")
        item.save(update_fields=["quantity"])

    return JsonResponse(
        {
            "success": True,
            "created": created,
            "item": {
                "inventory_name": inventory.name,
                "barcode": inventory.barcode,
                "part_number": inventory.part_number,
                "quantity": str(item.quantity),
                "unit_price": str(item.unit_price),
                "total_price": f"{float(item.total_price):.2f}",
            },
        }
    )


@login_required
def jobcard_delete_item(request, pk, item_pk):
    """Delete an item from a job card (AJAX POST)"""
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    jobcard = get_object_or_404(JobCard, pk=pk)

    try:
        # pylint: disable=no-member
        item = JobCardItem.objects.get(pk=item_pk, job_card=jobcard)
        item.delete()
        return JsonResponse({"success": True})
    except ObjectDoesNotExist:
        return JsonResponse({"error": "Item not found."}, status=404)


@login_required
def jobcard_update_item_qty(request, pk, item_pk):
    """Update quantity of an item on a job card (AJAX POST)"""

    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    jobcard = get_object_or_404(JobCard, pk=pk)
    try:
        # pylint: disable=no-member
        item = JobCardItem.objects.get(pk=item_pk, job_card=jobcard)
    except ObjectDoesNotExist:
        return JsonResponse({"error": "Item not found."}, status=404)

    try:
        new_qty = Decimal(request.POST.get("quantity", "0"))
        if new_qty < 0:
            return JsonResponse({"error": "Quantity cannot be negative."}, status=400)
    except InvalidOperation:
        return JsonResponse({"error": "Invalid quantity format."}, status=400)

    item.quantity = new_qty
    item.save(update_fields=["quantity"])

    # Calculate new grand total
    grand_total = sum(float(i.total_price) for i in jobcard.job_card_items.all())

    return JsonResponse(
        {
            "success": True,
            "item": {
                "id": item.id,
                "quantity": str(item.quantity),
                "total_price": f"{float(item.total_price):.2f}",
            },
            "grand_total": f"{grand_total:.2f}",
        }
    )


@login_required
def vehicle_search(request):
    """API endpoint to search existing job cards by vehicle number.

    Returns distinct (customer, vehicle_model, vehicle_number) combinations
    so the create-form side panel can auto-fill fields.
    """
    query = request.GET.get("q", "").strip()
    if len(query) < 2:
        return JsonResponse({"results": []})

    jobcards = (
        JobCard.objects.filter(
            Q(vehicle_number__icontains=query) | Q(customer__name__icontains=query)
        )
        .select_related("customer", "vehicle_model", "vehicle_model__make")
        .order_by("-created_at")[:20]
    )

    # Deduplicate by vehicle_number (keep the most recent)
    seen = set()
    results = []
    for jc in jobcards:
        if jc.vehicle_number in seen:
            continue
        seen.add(jc.vehicle_number)
        results.append(
            {
                "customer_id": jc.customer_id,
                "customer_name": str(jc.customer),
                "vehicle_model_id": jc.vehicle_model_id,
                "vehicle_model_name": (
                    str(jc.vehicle_model) if jc.vehicle_model else ""
                ),
                "vehicle_number": jc.vehicle_number,
            }
        )

    return JsonResponse({"results": results})


@login_required
def inventory_search(request):
    """API endpoint to search inventory items by brand, name, part_number, or barcode.

    Returns matching inventory items so the user can pick one to add to a job card.
    """
    query = request.GET.get("q", "").strip()
    if len(query) < 2:
        return JsonResponse({"results": []})

    base_qs = Inventory.objects.filter(
        Q(brand__icontains=query)
        | Q(name__icontains=query)
        | Q(part_number__icontains=query)
        | Q(barcode__icontains=query)
    )

    jobcard_id = request.GET.get("jobcard_id")
    jobcard_vehicle_model_id = None
    if jobcard_id:
        try:
            jobcard = JobCard.objects.get(pk=jobcard_id)
            if jobcard.vehicle_model_id:
                jobcard_vehicle_model_id = jobcard.vehicle_model_id
        except ObjectDoesNotExist:
            pass

    # Annotate compatibility at the DB level — no Python loop needed
    if jobcard_vehicle_model_id:
        from django.db.models import Exists, OuterRef

        base_qs = base_qs.annotate(
            is_compatible=Exists(
                Inventory.compatible_vehicles.through.objects.filter(
                    inventory_id=OuterRef("pk"),
                    vehiclemodel_id=jobcard_vehicle_model_id,
                )
            )
        )

    items = base_qs.order_by("name")[:10]

    results = [
        {
            "id": item.id,
            "brand": item.brand or "",
            "name": item.name,
            "part_number": item.part_number or "",
            "barcode": item.barcode,
            "selling_price": str(item.selling_price),
            "quantity": str(item.available_quantity),
            "compatibility": (
                "Compatible" if getattr(item, "is_compatible", False) else ""
            ),
        }
        for item in items
    ]

    return JsonResponse({"results": results})

"""Views for the inventory application."""

import base64
import io
from barcode import Code128
from barcode.writer import SVGWriter
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.views.generic import ListView, CreateView, UpdateView, DetailView, FormView
from django.views.generic.detail import SingleObjectMixin
from django.http import JsonResponse
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from decimal import Decimal
from django.db import transaction
from django.db.models import Q, Sum, F
from django.db.models.functions import Coalesce
from base.utility import render_paginated_response, table_sorting
from .models import Inventory, Category, UOM
from .forms import InventoryForm, CategoryForm, UOMForm, InventoryStockInForm
from .services import InventoryService

# ============================================
# INVENTORY ITEMS
# ============================================


@login_required
def inventory_list(request):
    """List all inventory items"""
    items_count = Inventory.objects.count()
    # Compute total stock asset valuation directly in database (quantity * cost_price)
    total_value = Inventory.objects.aggregate(
        total=Coalesce(Sum(F("quantity") * F("cost_price")), Decimal("0"))
    )["total"]
    return render(
        request,
        "inventory/main.html",
        {"items_count": items_count, "total_value": total_value},
    )


def get_data(request):
    """Return a filtered and sorted inventory queryset based on request params."""
    search_query = request.GET.get("q", "")

    queryset = (
        Inventory.objects.all()
        .select_related("category", "uom")
        .prefetch_related("compatible_vehicles__make")
    )
    if search_query:
        # Split query into words so "swift oil filter" matches items where
        # each word is found in at least one searchable field.
        terms = search_query.split()
        for term in terms:
            queryset = queryset.filter(
                Q(name__icontains=term)
                | Q(part_number__icontains=term)
                | Q(barcode__icontains=term)
                | Q(brand__icontains=term)
                | Q(category__name__icontains=term)
                | Q(compatible_vehicles__model_name__icontains=term)
                | Q(compatible_vehicles__make__name__icontains=term)
            )
        queryset = queryset.distinct()

    valid_sorts = table_sorting(
        request,
        valid_sorts=[
            "name",
            "part_number",
            "barcode",
            "quantity",
            "cost_price",
            "selling_price",
            "shelf_location",
            "created_at",
        ],
        default_sort="-created_at",
    )

    queryset = queryset.order_by(*valid_sorts)
    return queryset


@login_required
def fetch_inventory(request):
    """AJAX endpoint to fetch inventory with search, filter, and pagination."""
    items = get_data(request)

    return render_paginated_response(
        request,
        items,
        "inventory/fetch.html",
        per_page=10,
    )


class InventoryCreateView(
    LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, CreateView
):
    """View to create a new inventory item."""

    model = Inventory
    form_class = InventoryForm
    template_name = "inventory/form.html"
    permission_required = "inventory.add_inventory"
    success_url = reverse_lazy("inventory:list")
    extra_context = {"title": "Add New Item"}

    def get_initial(self):
        initial = super().get_initial()
        if not initial.get("category"):
            first_cat = Category.objects.first()
            if first_cat:
                initial["category"] = first_cat.pk
        if not initial.get("uom"):
            first_uom = UOM.objects.first()
            if first_uom:
                initial["uom"] = first_uom.pk
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if "category_form" not in context:
            from .forms import CategoryForm

            context["category_form"] = CategoryForm(prefix="modal-cat")
        if "uom_form" not in context:
            from .forms import UOMForm

            context["uom_form"] = UOMForm(prefix="modal-uom")
        return context

    def get_success_message(self, cleaned_data):
        return f"Item {self.object.name} added successfully."

    def get_success_url(self):
        return reverse("inventory:detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        form.instance.created_by = self.request.user

        with transaction.atomic():
            # Initial quantity needs to be saved but not double-counted by the service
            initial_quantity = form.instance.quantity
            form.instance.quantity = (
                0  # Temporarily reset to 0 so the service handles the addition
            )

            response = super().form_valid(form)

            # Create an initial inventory log if starting with stock
            if initial_quantity > 0:
                InventoryService.record_purchase(
                    inventory=self.object,
                    quantity=initial_quantity,
                    reference_number="Initial Stock",
                    notes="Stock added during item creation.",
                    user=self.request.user,
                )
        return response


class InventoryUpdateView(
    LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, UpdateView
):
    """View to update an existing inventory item."""

    model = Inventory
    form_class = InventoryForm
    template_name = "inventory/form.html"
    permission_required = "inventory.change_inventory"
    success_url = reverse_lazy("inventory:list")
    extra_context = {"title": "Edit Item", "is_edit": True}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if "category_form" not in context:
            from .forms import CategoryForm

            context["category_form"] = CategoryForm(prefix="modal-cat")
        if "uom_form" not in context:
            from .forms import UOMForm

            context["uom_form"] = UOMForm(prefix="modal-uom")
        return context

    def get_success_message(self, cleaned_data):
        return f"Item {self.object.name} updated successfully."

    def form_valid(self, form):
        with transaction.atomic():
            # Get the original object to know the previous quantity
            original = Inventory.objects.get(pk=self.object.pk)
            quantity_diff = form.instance.quantity - original.quantity

            # Reset form instance quantity back so the service handles the exact diff
            form.instance.quantity = original.quantity

            response = super().form_valid(form)

            if quantity_diff > 0:
                InventoryService.record_purchase(
                    inventory=self.object,
                    quantity=quantity_diff,
                    reference_number="Manual Adjustment",
                    notes="Stock manually increased during edit.",
                    user=self.request.user,
                )
            elif quantity_diff < 0:
                InventoryService.record_sale(
                    inventory=self.object,
                    quantity=abs(quantity_diff),
                    reference_number="Manual Adjustment",
                    notes="Stock manually decreased during edit.",
                    user=self.request.user,
                )
        return response


@login_required
@permission_required("inventory.delete_inventory", raise_exception=True)
def inventory_delete(request, pk):
    """Delete an inventory item"""
    item = get_object_or_404(Inventory, pk=pk)
    if request.method == "POST":
        item.delete()
        messages.success(request, "Item deleted successfully.")
        return redirect("inventory:list")

    return render(request, "inventory/delete.html", {"object": item})


class InventoryDetailView(LoginRequiredMixin, DetailView):
    """View to display details of an inventory item."""

    model = Inventory
    template_name = "inventory/detail.html"
    context_object_name = "item"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = f"Part: {self.object.part_number}"
        context["logs"] = self.object.inventory_logs.all().order_by("-transaction_date")
        context["stock_in_form"] = InventoryStockInForm(
            initial={
                "cost_price": self.object.cost_price,
                "selling_price": self.object.selling_price,
            }
        )
        return context


class InventoryStockInView(
    LoginRequiredMixin, PermissionRequiredMixin, SingleObjectMixin, FormView
):
    """View to handle POST for stocking in an inventory item."""

    model = Inventory
    form_class = InventoryStockInForm
    permission_required = "inventory.change_inventory"

    def post(self, request, *args, **kwargs):
        # The SingleObjectMixin needs the object populated to check permissions etc.
        self.object = self.get_object()
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        quantity = form.cleaned_data["quantity"]
        cost_price = form.cleaned_data["cost_price"]
        selling_price = form.cleaned_data["selling_price"]
        reference_number = form.cleaned_data["reference_number"]
        notes = form.cleaned_data["notes"]

        with transaction.atomic():
            # Update the prices
            self.object.cost_price = cost_price
            self.object.selling_price = selling_price
            self.object.save(update_fields=["cost_price", "selling_price"])

            # Create the purchase log and add quantity
            InventoryService.record_purchase(
                inventory=self.object,
                quantity=quantity,
                reference_number=reference_number,
                notes=notes,
                user=self.request.user,
            )

        messages.success(
            self.request,
            f"Successfully added {quantity} units to {self.object.name} "
            f"and updated prices.",
        )
        return super().form_valid(form)

    def form_invalid(self, form):
        # We redirect back with a generic error message.
        # For a full implementation, you could pass errors to the session
        # or render the detail view with the invalid form.
        messages.error(
            self.request,
            "Failed to stock in. Please check the form fields and try again.",
        )
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse("inventory:detail", kwargs={"pk": self.object.pk})


@login_required
def inventory_print_barcode(request, pk):
    """Generate and render barcode labels for an inventory item (like My_Billing)."""
    item = get_object_or_404(Inventory, pk=pk)

    # Ensure barcode exists
    if not item.barcode:
        item.create_barcode(save=True)

    # Generate Code128 SVG barcode without text/number below the barcode
    code128 = Code128(item.barcode, writer=SVGWriter())
    buffer = io.BytesIO()
    code128.write(buffer, options={"write_text": False})
    buffer.seek(0)
    barcode_svg = base64.b64encode(buffer.getvalue()).decode("utf-8")

    # Number of barcode stickers to print
    count_param = request.GET.get("count")
    if count_param and count_param.isdigit() and int(count_param) > 0:
        print_count = min(int(count_param), 100)
    else:
        print_count = 1

    context = {
        "values": item,
        "item": item,
        "barcode_svg": barcode_svg,
        "print_count": print_count,
        "count": print_count,
        "title": f"{item.barcode} - Barcode",
    }
    return render(request, "inventory/print_barcode.html", context)


# ============================================
# CATEGORIES
# ============================================


@login_required
def category_list(request):
    """List all categories"""
    categories = Category.objects.all().order_by("name")
    return render(request, "inventory/category/list.html", {"categories": categories})


@login_required
def category_create_ajax(request):
    """AJAX endpoint to create a new category."""
    if request.method == "POST":
        from .forms import CategoryForm

        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save(commit=False)
            category.created_by = request.user
            category.save()
            return JsonResponse(
                {
                    "success": True,
                    "category": {
                        "id": category.id,
                        "display": category.name,
                    },
                }
            )
        else:
            return JsonResponse({"success": False, "errors": form.errors}, status=400)
    return JsonResponse({"error": "Invalid request method"}, status=405)


class CategoryCreateView(
    LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, CreateView
):
    """View to create a new category."""

    model = Category
    form_class = CategoryForm
    template_name = "inventory/category/form.html"
    permission_required = "inventory.add_category"
    success_url = reverse_lazy("inventory:category_list")
    extra_context = {"title": "Add Category"}

    def get_success_message(self, cleaned_data):
        return f"Category {self.object.name} added successfully."

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)


class CategoryUpdateView(
    LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, UpdateView
):
    """View to update an existing category."""

    model = Category
    form_class = CategoryForm
    template_name = "inventory/category/form.html"
    permission_required = "inventory.change_category"
    success_url = reverse_lazy("inventory:category_list")
    extra_context = {"title": "Edit Category", "is_edit": True}

    def get_success_message(self, cleaned_data):
        return f"Category {self.object.name} updated successfully."


@login_required
@permission_required("inventory.delete_category", raise_exception=True)
def category_delete(request, pk):
    """Delete a category"""
    category = get_object_or_404(Category, pk=pk)
    if request.method == "POST":
        try:
            category.delete()
            messages.success(request, "Category deleted successfully.")
        except Exception as e:  # pylint: disable=broad-exception-caught
            messages.error(request, f"Error deleting category: {str(e)}")
        return redirect("inventory:category_list")

    return render(request, "inventory/category/delete.html", {"object": category})


# ============================================
# UNITS OF MEASUREMENT (UOM)
# ============================================


@login_required
def uom_list(request):
    """List all UOMs"""
    uoms = UOM.objects.all().order_by("name")
    return render(request, "inventory/uom/list.html", {"uoms": uoms})


@login_required
def uom_create_ajax(request):
    """AJAX endpoint to create a new UOM."""
    if request.method == "POST":
        from .forms import UOMForm

        form = UOMForm(request.POST)
        if form.is_valid():
            uom = form.save(commit=False)
            uom.created_by = request.user
            uom.save()
            return JsonResponse(
                {
                    "success": True,
                    "uom": {
                        "id": uom.id,
                        "display": uom.name,
                    },
                }
            )
        else:
            return JsonResponse({"success": False, "errors": form.errors}, status=400)
    return JsonResponse({"error": "Invalid request method"}, status=405)


class UOMCreateView(
    LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, CreateView
):
    """View to create a new unit of measurement."""

    model = UOM
    form_class = UOMForm
    template_name = "inventory/uom/form.html"
    permission_required = "inventory.add_uom"
    success_url = reverse_lazy("inventory:uom_list")
    extra_context = {"title": "Add Unit of Measure"}

    def get_success_message(self, cleaned_data):
        return f"Unit {self.object.name} added successfully."

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)


class UOMUpdateView(
    LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, UpdateView
):
    """View to update an existing unit of measurement."""

    model = UOM
    form_class = UOMForm
    template_name = "inventory/uom/form.html"
    permission_required = "inventory.change_uom"
    success_url = reverse_lazy("inventory:uom_list")
    extra_context = {"title": "Edit Unit of Measure", "is_edit": True}

    def get_success_message(self, cleaned_data):
        return f"Unit {self.object.name} updated successfully."


@login_required
@permission_required("inventory.delete_uom", raise_exception=True)
def uom_delete(request, pk):
    """Delete a UOM"""
    uom = get_object_or_404(UOM, pk=pk)
    if request.method == "POST":
        try:
            uom.delete()
            messages.success(request, "Unit deleted successfully.")
        except Exception as e:  # pylint: disable=broad-exception-caught
            messages.error(request, f"Error deleting unit: {str(e)}")
        return redirect("inventory:uom_list")

    return render(request, "inventory/uom/delete.html", {"object": uom})

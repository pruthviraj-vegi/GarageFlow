from django.shortcuts import render
from django.db.models import Q
from .models import VehicleModel, VehicleMake
from .forms import VehicleModelForm, VehicleMakeForm
from django.urls import reverse_lazy
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic import DetailView, ListView

from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.decorators import login_required
from base.utility import render_paginated_response, table_sorting


@login_required
def vehicle_list(request):
    """List all vehicle models"""
    vehicles_count = VehicleModel.objects.count()
    return render(
        request,
        "vehicle/list.html",
        {"title": "Vehicle Models", "vehicles_count": vehicles_count},
    )


def get_data(request):
    """Return a filtered and sorted vehicle model queryset based on request params."""
    search_query = request.GET.get("q", "")

    queryset = VehicleModel.objects.all().select_related("make")
    if search_query:
        queryset = queryset.filter(
            Q(make__name__icontains=search_query)
            | Q(model_name__icontains=search_query)
            | Q(transmission__icontains=search_query)
            | Q(fuel_type__icontains=search_query)
        )

    valid_sorts = table_sorting(
        request,
        valid_sorts=[
            "make__name",
            "model_name",
            "fuel_type",
            "transmission",
            "created_at",
        ],
        default_sort="-created_at",
    )

    queryset = queryset.order_by(*valid_sorts)
    return queryset


@login_required
def fetch_vehicles(request):
    """AJAX endpoint to fetch vehicle models with search, filter, and pagination."""
    items = get_data(request)

    return render_paginated_response(
        request,
        items,
        "vehicle/fetch.html",
        per_page=10,
    )


@login_required
def vehicle_model_create_ajax(request):
    """AJAX endpoint to create a new vehicle model."""
    if request.method == "POST":
        from .forms import VehicleModelForm
        from django.http import JsonResponse

        form = VehicleModelForm(request.POST)
        if form.is_valid():
            vehicle_model = form.save(commit=False)
            vehicle_model.created_by = request.user
            vehicle_model.save()
            return JsonResponse(
                {
                    "success": True,
                    "vehicle": {
                        "id": vehicle_model.id,
                        "display": vehicle_model.display_name,
                    },
                }
            )
        else:
            return JsonResponse({"success": False, "errors": form.errors}, status=400)
    return JsonResponse({"error": "Invalid request method"}, status=405)


class VehicleModelDetailView(DetailView):
    model = VehicleModel
    template_name = "vehicle/detail.html"
    context_object_name = "vehicle"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = f"{self.object.make.name} {self.object.model_name}"
        return context


class VehicleCreateView(
    LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, CreateView
):
    model = VehicleModel
    form_class = VehicleModelForm
    template_name = "vehicle/form.html"
    permission_required = "vehicle.add_vehiclemodel"
    success_url = reverse_lazy("vehicle:list")
    success_message = "Vehicle model created successfully."
    extra_context = {"title": "Add New Vehicle Model"}

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)


class VehicleUpdateView(
    LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, UpdateView
):
    model = VehicleModel
    form_class = VehicleModelForm
    template_name = "vehicle/form.html"
    permission_required = "vehicle.change_vehiclemodel"
    success_url = reverse_lazy("vehicle:list")
    success_message = "Vehicle model updated successfully."
    extra_context = {"title": "Edit Vehicle Model", "is_edit": True}


class VehicleDeleteView(
    LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, DeleteView
):
    model = VehicleModel
    template_name = "vehicle/delete.html"
    permission_required = "vehicle.delete_vehiclemodel"
    success_url = reverse_lazy("vehicle:list")
    success_message = "Vehicle model deleted successfully."


class VehicleMakeListView(ListView):
    model = VehicleMake
    template_name = "vehicle/maker/list.html"
    context_object_name = "makes"
    ordering = ["name"]
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset()
        query = self.request.GET.get("q")
        if query:
            queryset = queryset.filter(name__icontains=query)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Vehicle Makes"
        context["search_query"] = self.request.GET.get("q", "")
        return context


class VehicleMakeCreateView(
    LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, CreateView
):
    model = VehicleMake
    form_class = VehicleMakeForm
    template_name = "vehicle/maker/form.html"
    permission_required = "vehicle.add_vehiclemake"
    success_url = reverse_lazy("vehicle:make-list")
    success_message = "Vehicle make created successfully."
    extra_context = {"title": "Add New Vehicle Make"}

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)


class VehicleMakeUpdateView(
    LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, UpdateView
):
    model = VehicleMake
    form_class = VehicleMakeForm
    template_name = "vehicle/maker/form.html"
    permission_required = "vehicle.change_vehiclemake"
    success_url = reverse_lazy("vehicle:make-list")
    success_message = "Vehicle make updated successfully."
    extra_context = {"title": "Edit Vehicle Make", "is_edit": True}


class VehicleMakeDeleteView(
    LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, DeleteView
):
    model = VehicleMake
    template_name = "vehicle/maker/delete.html"
    permission_required = "vehicle.delete_vehiclemake"
    success_url = reverse_lazy("vehicle:make-list")
    success_message = "Vehicle make deleted successfully."

from django.urls import path
from . import views

app_name = "vehicle"

urlpatterns = [
    path("", views.vehicle_list, name="list"),
    path("fetch/", views.fetch_vehicles, name="fetch"),
    path("api/create/", views.vehicle_model_create_ajax, name="api_create_model"),
    path("add/", views.VehicleCreateView.as_view(), name="add"),
    path("<int:pk>/", views.VehicleModelDetailView.as_view(), name="detail"),
    path("<int:pk>/edit/", views.VehicleUpdateView.as_view(), name="edit"),
    path("<int:pk>/delete/", views.VehicleDeleteView.as_view(), name="delete"),
    # Vehicle Make URLs
    path("makes/", views.VehicleMakeListView.as_view(), name="make-list"),
    path("makes/add/", views.VehicleMakeCreateView.as_view(), name="make-add"),
    path(
        "makes/<int:pk>/edit/", views.VehicleMakeUpdateView.as_view(), name="make-edit"
    ),
    path(
        "makes/<int:pk>/delete/",
        views.VehicleMakeDeleteView.as_view(),
        name="make-delete",
    ),
]

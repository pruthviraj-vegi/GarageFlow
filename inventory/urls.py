"""URL routing for the inventory app."""

from django.urls import path
from . import views

app_name = "inventory"  # pylint: disable=invalid-name

urlpatterns = [
    # Inventory Items
    path("", views.inventory_list, name="list"),
    path("fetch/", views.fetch_inventory, name="fetch"),
    path("add/", views.InventoryCreateView.as_view(), name="add"),
    path(
        "<int:pk>/", views.InventoryDetailView.as_view(), name="detail"
    ),  # pylint: disable=no-member
    path("<int:pk>/print-barcode/", views.inventory_print_barcode, name="print_barcode"),
    path("<int:pk>/stock-in/", views.InventoryStockInView.as_view(), name="stock_in"),
    path("<int:pk>/edit/", views.InventoryUpdateView.as_view(), name="edit"),
    path("<int:pk>/delete/", views.inventory_delete, name="delete"),
    # Categories
    path("categories/", views.category_list, name="category_list"),
    path(
        "api/categories/create/", views.category_create_ajax, name="api_create_category"
    ),
    path("categories/add/", views.CategoryCreateView.as_view(), name="category_add"),
    path(
        "categories/<int:pk>/edit/",
        views.CategoryUpdateView.as_view(),
        name="category_edit",
    ),
    path("categories/<int:pk>/delete/", views.category_delete, name="category_delete"),
    # UOM
    path("uom/", views.uom_list, name="uom_list"),
    path("api/uom/create/", views.uom_create_ajax, name="api_create_uom"),
    path("uom/add/", views.UOMCreateView.as_view(), name="uom_add"),
    path("uom/<int:pk>/edit/", views.UOMUpdateView.as_view(), name="uom_edit"),
    path("uom/<int:pk>/delete/", views.uom_delete, name="uom_delete"),
]

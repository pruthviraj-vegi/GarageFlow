"""URL configuration for the jobcard app."""

from django.urls import path
from . import views

app_name = "jobcard"  # pylint: disable=invalid-name

urlpatterns = [
    path("", views.jobcard_list, name="list"),
    path("fetch/", views.fetch_jobcards, name="fetch"),
    path("add/", views.JobCardCreateView.as_view(), name="add"),
    path("<int:pk>/", views.jobcard_detail, name="detail"),
    path("<int:pk>/edit/", views.JobCardUpdateView.as_view(), name="edit"),
    path("<int:pk>/delete/", views.jobcard_delete, name="delete"),
    path("<int:pk>/submit/", views.jobcard_submit, name="submit"),
    path("api/<int:pk>/", views.jobcard_api_detail, name="api_detail"),
    path("api/<int:pk>/add-item/", views.jobcard_add_item, name="api_add_item"),
    path(
        "api/<int:pk>/item/<int:item_pk>/delete/",
        views.jobcard_delete_item,
        name="api_delete_item",
    ),
    path(
        "api/<int:pk>/item/<int:item_pk>/update-qty/",
        views.jobcard_update_item_qty,
        name="api_update_item_qty",
    ),
    path("api/vehicle-search/", views.vehicle_search, name="api_vehicle_search"),
    path(
        "api/inventory-search/",
        views.inventory_search,
        name="api_inventory_search",
    ),
]

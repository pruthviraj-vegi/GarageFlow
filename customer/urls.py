from django.urls import path
from . import views

app_name = "customer"

urlpatterns = [
    path("", views.home, name="list"),
    path("fetch/", views.fetch_customers, name="fetch"),
    path("add/", views.CustomerCreateView.as_view(), name="add"),
    path("<int:pk>/edit/", views.CustomerUpdateView.as_view(), name="edit"),
    path("<int:pk>/delete/", views.customer_delete, name="delete"),
    path("api/create/", views.customer_create_ajax, name="api_create"),
]

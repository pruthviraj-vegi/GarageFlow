from django.urls import path
from . import views

app_name = "user"

urlpatterns = [
    path("", views.user_list, name="list"),
    path("add/", views.UserCreateView.as_view(), name="add"),
    path("<int:pk>/edit/", views.UserUpdateView.as_view(), name="edit"),
    path("<int:pk>/delete/", views.user_delete, name="delete"),
]

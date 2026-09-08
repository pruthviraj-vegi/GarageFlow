from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from .forms import CustomUserCreationForm, CustomUserChangeForm

User = get_user_model()


@login_required
def user_list(request):
    """List all users"""
    users = User.objects.prefetch_related("groups").all().order_by("-date_joined")
    return render(request, "user/main.html", {"users": users})


class UserCreateView(PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    model = User
    form_class = CustomUserCreationForm
    template_name = "user/form.html"
    permission_required = "user.add_customuser"
    success_url = reverse_lazy("user:list")
    extra_context = {"title": "Add New User"}

    def get_success_message(self, cleaned_data):
        return f"User {self.object.get_full_name()} created successfully."

    def form_invalid(self, form):
        messages.error(self.request, "Failed to create user.")
        return super().form_invalid(form)


class UserUpdateView(PermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    model = User
    form_class = CustomUserChangeForm
    template_name = "user/form.html"
    permission_required = "user.change_customuser"
    success_url = reverse_lazy("user:list")
    extra_context = {"title": "Edit User", "is_edit": True}

    def get_success_message(self, cleaned_data):
        return f"User {self.object.get_full_name()} updated successfully."


@login_required
@permission_required("user.delete_customuser", raise_exception=True)
def user_delete(request, pk):
    """Delete a user"""
    user = get_object_or_404(User, pk=pk)
    if request.method == "POST":
        name = user.get_full_name()
        user.delete()
        messages.success(request, f"User {name} deleted successfully.")
        return redirect("user:list")
    return render(request, "user/delete.html", {"object": user})

import re

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth.models import Group

User = get_user_model()


# ============================================
# SHARED FORM VALIDATION MIXIN
# ============================================


class UserFormMixin:
    """Shared validation logic for both Create and Update user forms."""

    def clean_phone(self):
        phone = self.cleaned_data.get("phone", "").strip()
        if not phone:
            raise forms.ValidationError("Phone number is required.")
        if not re.match(r"^\d{10}$", phone):
            raise forms.ValidationError("Phone number must be exactly 10 digits.")

        # Uniqueness check (exclude current instance on update)
        qs = User.objects.filter(phone=phone)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("A user with this phone number already exists.")
        return phone

    def clean_first_name(self):
        name = self.cleaned_data.get("first_name", "").strip()
        if not name:
            raise forms.ValidationError("First name is required.")
        if len(name) < 2:
            raise forms.ValidationError("First name must be at least 2 characters.")
        if not re.match(r"^[a-zA-Z\s\-'.]+$", name):
            raise forms.ValidationError(
                "First name can only contain letters, spaces, hyphens, and apostrophes."
            )
        return name.title()

    def clean_last_name(self):
        name = self.cleaned_data.get("last_name", "").strip()
        if not name:
            raise forms.ValidationError("Last name is required.")
        if len(name) < 2:
            raise forms.ValidationError("Last name must be at least 2 characters.")
        if not re.match(r"^[a-zA-Z\s\-'.]+$", name):
            raise forms.ValidationError(
                "Last name can only contain letters, spaces, hyphens, and apostrophes."
            )
        return name.title()

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip().lower()
        if email:
            # Uniqueness check (exclude current instance on update)
            qs = User.objects.filter(email=email)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError(
                    "A user with this email address already exists."
                )
        return email


# ============================================
# USER CREATION FORM
# ============================================


class CustomUserCreationForm(UserFormMixin, UserCreationForm):
    groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={"class": "form-check-input"}),
        label="Roles / Groups",
        help_text="Select one or more roles/groups for this user (e.g. Service Advisor, Inventory Manager, Cashier, Admin)",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add 'form-input' class to password fields inherited from UserCreationForm
        for field_name in ["password1", "password2"]:
            if field_name in self.fields:
                self.fields[field_name].widget.attrs["class"] = "form-input"

    class Meta:
        model = User
        fields = (
            "phone",
            "first_name",
            "last_name",
            "groups",
            "email",
            "is_active",
            "is_staff",
        )
        widgets = {
            "phone": forms.TextInput(
                attrs={"class": "form-input", "placeholder": "10-digit phone number"}
            ),
            "first_name": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "First Name",
                    "autofocus": True,
                }
            ),
            "last_name": forms.TextInput(
                attrs={"class": "form-input", "placeholder": "Last Name"}
            ),
            "email": forms.EmailInput(
                attrs={"class": "form-input", "placeholder": "Email (optional)"}
            ),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_staff": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            if user.groups.filter(name__in=["Admin", "Administrator"]).exists():
                user.is_staff = True
                user.save(update_fields=["is_staff"])
        return user


# ============================================
# USER UPDATE FORM
# ============================================


class CustomUserChangeForm(UserFormMixin, UserChangeForm):
    password = None  # Exclude password field from edit form

    groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={"class": "form-check-input"}),
        label="Roles / Groups",
        help_text="Select one or more roles/groups for this user",
    )

    class Meta:
        model = User
        fields = (
            "phone",
            "first_name",
            "last_name",
            "groups",
            "email",
            "is_active",
            "is_staff",
        )
        widgets = {
            "phone": forms.TextInput(attrs={"class": "form-input"}),
            "first_name": forms.TextInput(attrs={"class": "form-input"}),
            "last_name": forms.TextInput(attrs={"class": "form-input"}),
            "email": forms.EmailInput(attrs={"class": "form-input"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_staff": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            if user.groups.filter(name__in=["Admin", "Administrator"]).exists():
                user.is_staff = True
                user.save(update_fields=["is_staff"])
        return user

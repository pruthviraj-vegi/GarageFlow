import re

from django import forms
from .models import Customer


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ["name", "phone", "address", "notes"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "Customer Name",
                    "autofocus": True,
                }
            ),
            "phone": forms.TextInput(
                attrs={"class": "form-input", "placeholder": "10-digit Phone Number"}
            ),
            "address": forms.TextInput(
                attrs={"class": "form-input", "placeholder": "Address"}
            ),
            "notes": forms.Textarea(
                attrs={"class": "form-input", "placeholder": "Notes", "rows": 3}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # On validation errors, move autofocus to the first errored field
        if self.errors:
            # Remove autofocus from all fields first
            for field in self.fields.values():
                field.widget.attrs.pop("autofocus", None)
            # Set autofocus on the first field with an error
            for field_name in self.fields:
                if field_name in self.errors:
                    self.fields[field_name].widget.attrs["autofocus"] = True
                    break

    # ─── Name validation ───
    def clean_name(self):
        name = self.cleaned_data.get("name", "").strip()
        if not name:
            raise forms.ValidationError("Customer name is required.")
        if len(name) < 2:
            raise forms.ValidationError("Name must be at least 2 characters.")
        if len(name) > 100:
            raise forms.ValidationError("Name must not exceed 100 characters.")
        if not re.match(r"^[a-zA-Z\s\-'.]+$", name):
            raise forms.ValidationError(
                "Name can only contain letters, spaces, hyphens, and apostrophes."
            )
        return name.title()

    # ─── Phone validation ───
    def clean_phone(self):
        phone = self.cleaned_data.get("phone", "").strip()
        if not phone:
            raise forms.ValidationError("Phone number is required.")
        if not re.match(r"^\d{10}$", phone):
            raise forms.ValidationError("Phone number must be exactly 10 digits.")

        # Uniqueness check (exclude current instance on update)
        qs = Customer.objects.filter(phone=phone)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(
                "A customer with this phone number already exists."
            )
        return phone

    # ─── Address validation ───
    def clean_address(self):
        address = self.cleaned_data.get("address", "")
        if address:
            address = address.strip()
            if len(address) < 5:
                raise forms.ValidationError(
                    "Address must be at least 5 characters if provided."
                )
            if len(address) > 255:
                raise forms.ValidationError("Address must not exceed 255 characters.")
        return address or None

    # ─── Notes validation ───
    def clean_notes(self):
        notes = self.cleaned_data.get("notes", "")
        if notes:
            notes = notes.strip()
            if len(notes) > 1000:
                raise forms.ValidationError("Notes must not exceed 1000 characters.")
        return notes or None

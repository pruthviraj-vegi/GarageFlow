import re

from django import forms
from .models import VehicleModel, VehicleMake


class VehicleMakeForm(forms.ModelForm):
    class Meta:
        model = VehicleMake
        fields = ["name"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "Make Name (e.g. Toyota)",
                    "autofocus": True,
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.errors:
            for field in self.fields.values():
                field.widget.attrs.pop("autofocus", None)
            for field_name in self.fields:
                if field_name in self.errors:
                    self.fields[field_name].widget.attrs["autofocus"] = True
                    break

    def clean_name(self):
        name = self.cleaned_data.get("name", "").strip()
        if not name:
            raise forms.ValidationError("Make name is required.")
        if len(name) < 2:
            raise forms.ValidationError("Make name must be at least 2 characters.")
        if len(name) > 100:
            raise forms.ValidationError("Make name must not exceed 100 characters.")
        if not re.match(r"^[a-zA-Z\s\-'.]+$", name):
            raise forms.ValidationError(
                "Make name can only contain letters, spaces, hyphens, and apostrophes."
            )
        # Uniqueness check (exclude current instance on update)
        qs = VehicleMake.objects.filter(name__iexact=name)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("A vehicle make with this name already exists.")
        return name.title()


class VehicleModelForm(forms.ModelForm):
    class Meta:
        model = VehicleModel
        fields = ["make", "model_name", "fuel_type", "transmission", "notes"]
        widgets = {
            "make": forms.Select(attrs={"class": "form-select", "autofocus": True}),
            "model_name": forms.TextInput(
                attrs={"class": "form-input", "placeholder": "e.g. Corolla"}
            ),
            "fuel_type": forms.Select(attrs={"class": "form-select"}),
            "transmission": forms.Select(attrs={"class": "form-select"}),
            "notes": forms.Textarea(
                attrs={"class": "form-input", "placeholder": "Notes", "rows": 3}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.errors:
            for field in self.fields.values():
                field.widget.attrs.pop("autofocus", None)
            for field_name in self.fields:
                if field_name in self.errors:
                    self.fields[field_name].widget.attrs["autofocus"] = True
                    break

    def clean_model_name(self):
        name = self.cleaned_data.get("model_name", "").strip()
        if not name:
            raise forms.ValidationError("Model name is required.")
        if len(name) < 2:
            raise forms.ValidationError("Model name must be at least 2 characters.")
        if len(name) > 100:
            raise forms.ValidationError("Model name must not exceed 100 characters.")
        return name

    def clean_notes(self):
        notes = self.cleaned_data.get("notes", "")
        if notes:
            notes = notes.strip()
            if len(notes) > 1000:
                raise forms.ValidationError("Notes must not exceed 1000 characters.")
        return notes or ""

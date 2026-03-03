"""Forms for the inventory application."""

from django import forms
from .models import Inventory, Category, UOM


# ============================================
# SHARED AUTOFOCUS MIXIN
# ============================================


class AutofocusErrorMixin:
    """Move autofocus to the first errored field on validation failure."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.errors:
            for field in self.fields.values():
                field.widget.attrs.pop("autofocus", None)
            for field_name in self.fields:
                if field_name in self.errors:
                    self.fields[field_name].widget.attrs["autofocus"] = True
                    break


# ============================================
# INVENTORY FORM
# ============================================


class InventoryForm(AutofocusErrorMixin, forms.ModelForm):
    """Form for creating and updating Inventory items."""

    class Meta:
        """Meta configuration for InventoryForm."""

        model = Inventory
        fields = [
            "brand",
            "name",
            "part_number",
            "barcode",
            "category",
            "uom",
            "compatible_vehicles",
            "compatibility_notes",
            "cost_price",
            "selling_price",
            "quantity",
            "low_stock",
            "shelf_location",
            "description",
        ]
        widgets = {
            "brand": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "Brand",
                    "autofocus": True,
                }
            ),
            "name": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "Part Name",
                }
            ),
            "part_number": forms.TextInput(
                attrs={"class": "form-input", "placeholder": "Part Number"}
            ),
            "barcode": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "Barcode (auto-generated if empty)",
                }
            ),
            "category": forms.Select(attrs={"class": "form-select"}),
            "uom": forms.Select(attrs={"class": "form-select"}),
            "compatible_vehicles": forms.SelectMultiple(
                attrs={
                    "class": "form-select",
                    "data-placeholder": "Select compatible vehicles",
                }
            ),
            "compatibility_notes": forms.Textarea(
                attrs={
                    "class": "form-input",
                    "placeholder": "Additional compatibility info or universal part notes",
                    "rows": 3,
                }
            ),
            "cost_price": forms.NumberInput(
                attrs={"class": "form-input", "placeholder": "0.00", "step": "1"}
            ),
            "selling_price": forms.NumberInput(
                attrs={"class": "form-input", "placeholder": "0.00", "step": "1"}
            ),
            "quantity": forms.NumberInput(
                attrs={"class": "form-input", "placeholder": "0", "step": "1"}
            ),
            "low_stock": forms.NumberInput(
                attrs={"class": "form-input", "placeholder": "0", "step": "1"}
            ),
            "shelf_location": forms.TextInput(
                attrs={"class": "form-input", "placeholder": "e.g. A1-B2"}
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-input",
                    "placeholder": "Description",
                    "rows": 3,
                    "type": "text",
                }
            ),
        }

    def clean_name(self):
        """Validate the inventory item name."""
        name = self.cleaned_data.get("name", "").strip()
        if not name:
            raise forms.ValidationError("Item name is required.")
        if len(name) < 2:
            raise forms.ValidationError("Item name must be at least 2 characters.")
        if len(name) > 200:
            raise forms.ValidationError("Item name must not exceed 200 characters.")
        return name

    def clean_part_number(self):
        """Validate the inventory part number to ensure uniqueness."""
        pn = self.cleaned_data.get("part_number")
        if pn:
            pn = pn.strip()
            if len(pn) > 100:
                raise forms.ValidationError(
                    "Part number must not exceed 100 characters."
                )
            # Uniqueness check
            qs = Inventory.objects.filter(part_number=pn)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError(
                    "An item with this part number already exists."
                )
            return pn
        return None

    def clean_barcode(self):
        """Validate the inventory barcode to ensure uniqueness."""
        barcode = self.cleaned_data.get("barcode", "").strip()
        if barcode:
            if len(barcode) > 20:
                raise forms.ValidationError("Barcode must not exceed 20 characters.")
            qs = Inventory.objects.filter(barcode=barcode)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError("An item with this barcode already exists.")
        return barcode

    def clean(self):
        cleaned_data = super().clean()
        cost = cleaned_data.get("cost_price")
        selling = cleaned_data.get("selling_price")

        if cost is not None and cost <= 0:
            self.add_error("cost_price", "Cost price must be greater than zero.")
        if selling is not None and selling <= 0:
            self.add_error("selling_price", "Selling price must be greater than zero.")

        return cleaned_data


# ============================================
# STOCK IN FORM
# ============================================


class InventoryStockInForm(forms.Form):
    """Form to process stock in (purchases) from the detail view."""

    quantity = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(
            attrs={
                "class": "form-input",
                "placeholder": "Enter quantity",
                "autofocus": True,
            }
        ),
    )
    cost_price = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0.01,
        widget=forms.NumberInput(
            attrs={"class": "form-input", "placeholder": "0.00", "step": "0.01"}
        ),
    )
    selling_price = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0.01,
        widget=forms.NumberInput(
            attrs={"class": "form-input", "placeholder": "0.00", "step": "0.01"}
        ),
    )
    reference_number = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-input", "placeholder": "Invoice / Bill #"}
        ),
    )
    notes = forms.CharField(
        widget=forms.Textarea(
            attrs={"class": "form-input", "placeholder": "Optional notes...", "rows": 2}
        ),
        required=False,
    )


# ============================================
# CATEGORY FORM
# ============================================


class CategoryForm(AutofocusErrorMixin, forms.ModelForm):
    """Form for creating and updating Categories."""

    class Meta:
        """Meta configuration for CategoryForm."""

        model = Category
        fields = ["name", "parent", "description"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "Category Name",
                    "autofocus": True,
                }
            ),
            "parent": forms.Select(attrs={"class": "form-select"}),
            "description": forms.Textarea(
                attrs={"class": "form-input", "placeholder": "Description", "rows": 3}
            ),
        }

    def clean_name(self):
        """Validate the category name."""
        name = self.cleaned_data.get("name", "").strip()
        if not name:
            raise forms.ValidationError("Category name is required.")
        if len(name) < 2:
            raise forms.ValidationError("Category name must be at least 2 characters.")
        if len(name) > 100:
            raise forms.ValidationError("Category name must not exceed 100 characters.")
        qs = Category.objects.filter(name__iexact=name)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("A category with this name already exists.")
        return name


# ============================================
# UOM FORM
# ============================================


class UOMForm(AutofocusErrorMixin, forms.ModelForm):
    """Form for creating and updating Units of Measurement (UOM)."""

    class Meta:
        """Meta configuration for UOMForm."""

        model = UOM
        fields = ["name", "description"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "Unit Name (e.g., pcs, kg)",
                    "autofocus": True,
                }
            ),
            "description": forms.Textarea(
                attrs={"class": "form-input", "placeholder": "Description", "rows": 3}
            ),
        }

    def clean_name(self):
        """Validate the UOM name."""
        name = self.cleaned_data.get("name", "").strip()
        if not name:
            raise forms.ValidationError("Unit name is required.")
        if len(name) < 1:
            raise forms.ValidationError("Unit name must be at least 1 character.")
        if len(name) > 50:
            raise forms.ValidationError("Unit name must not exceed 50 characters.")
        qs = UOM.objects.filter(name__iexact=name)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("A unit with this name already exists.")
        return name

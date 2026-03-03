from django import forms
from .models import Invoice


class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = [
            "customer",
            "job_card",
            "total_amount",
            "notes",
        ]
        widgets = {
            "customer": forms.Select(attrs={"class": "form-select"}),
            "job_card": forms.Select(attrs={"class": "form-select"}),
            "total_amount": forms.NumberInput(
                attrs={"class": "form-input", "placeholder": "0.00", "step": "0.01"}
            ),
            "notes": forms.Textarea(
                attrs={"class": "form-textarea", "placeholder": "Notes", "rows": 3}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # On validation errors, move autofocus to the first errored field
        if self.errors:
            for field in self.fields.values():
                field.widget.attrs.pop("autofocus", None)
            for field_name in self.fields:
                if field_name in self.errors:
                    self.fields[field_name].widget.attrs["autofocus"] = True
                    break

    # ─── Customer validation ───
    def clean_customer(self):
        customer = self.cleaned_data.get("customer")
        if not customer:
            raise forms.ValidationError("Customer is required.")
        return customer

    # ─── Total amount validation ───
    def clean_total_amount(self):
        total = self.cleaned_data.get("total_amount")
        if total is not None:
            if total < 0:
                raise forms.ValidationError("Total amount cannot be negative.")
            if total > 99999999.99:
                raise forms.ValidationError(
                    "Total amount seems too high. Please verify."
                )
        return total

    # ─── Notes validation ───
    def clean_notes(self):
        notes = self.cleaned_data.get("notes", "")
        if notes:
            notes = notes.strip()
            if len(notes) > 1000:
                raise forms.ValidationError("Notes must not exceed 1000 characters.")
        return notes or ""

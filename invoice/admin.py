from django.contrib import admin
from .models import Invoice, InvoiceItem


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 1
    readonly_fields = ("total_price",)


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = (
        "invoice_number",
        "customer",
        "job_card",
        "total_amount",
        "created_at",
    )
    list_filter = ("created_at",)
    search_fields = ("invoice_number", "customer__name", "job_card__job_card_number")
    readonly_fields = ("invoice_number", "created_at", "updated_at")
    inlines = [InvoiceItemInline]
    date_hierarchy = "created_at"

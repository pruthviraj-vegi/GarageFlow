from django.contrib import admin
from .models import JobCard, JobCardItem


class JobCardItemInline(admin.TabularInline):
    """Inline administration for Job Card Items."""

    model = JobCardItem
    extra = 1


@admin.register(JobCard)
class JobCardAdmin(admin.ModelAdmin):
    """Admin interface for Job Card."""

    list_display = (
        "job_card_number",
        "customer",
        "vehicle_number",
        "status",
        "created_at",
    )
    list_filter = ("status", "created_at", "updated_at")
    search_fields = ("job_card_number", "customer__name", "vehicle_number")
    readonly_fields = ("job_card_number", "completed_at", "cancelled_at")
    inlines = [JobCardItemInline]


@admin.register(JobCardItem)
class JobCardItemAdmin(admin.ModelAdmin):
    """Admin interface for Job Card Item."""

    list_display = ("job_card", "inventory", "quantity", "unit_price", "total_price")
    search_fields = ("job_card__job_card_number", "inventory__name")

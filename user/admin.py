from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser


class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ("phone", "first_name", "last_name", "primary_role", "is_staff", "is_active")
    list_filter = ("is_staff", "is_superuser", "is_active", "groups")
    fieldsets = (
        (None, {"fields": ("phone", "password")}),
        (
            "Personal Info",
            {"fields": ("first_name", "last_name", "email", "employee_id", "address")},
        ),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("phone", "first_name", "last_name", "password"),
            },
        ),
    )
    filter_horizontal = ("groups", "user_permissions")
    search_fields = ("phone", "first_name", "last_name", "email", "employee_id")
    ordering = ("phone",)


admin.site.register(CustomUser, CustomUserAdmin)

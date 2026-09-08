from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.db import models
from django.utils import timezone
from base.utility import phone_regex, generate_unique_code


# ============================================
# CUSTOM USER MANAGER
# ============================================


class CustomUserManager(BaseUserManager):
    """Custom user manager for phone-based authentication"""

    def create_user(self, phone, password=None, **extra_fields):
        """Create and save a regular user"""
        if not phone:
            raise ValueError("The Phone number field must be set")

        # Ensure phone is exactly 10 digits
        phone = str(phone).strip()
        if len(phone) != 10 or not phone.isdigit():
            raise ValueError("Phone number must be exactly 10 digits")

        user = self.model(phone=phone, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone, password=None, **extra_fields):
        """Create and save a superuser"""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(phone, password, **extra_fields)


# ============================================
# CUSTOM USER MODEL
# ============================================


class CustomUser(AbstractBaseUser, PermissionsMixin):
    """Custom User model with phone-based authentication and group-based permissions"""

    # Authentication - Phone number is the primary identifier
    phone = models.CharField(
        validators=[phone_regex],
        max_length=10,
        unique=True,
        verbose_name="Phone Number",
        help_text="10-digit phone number for login",
    )

    # Personal Information
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)

    # Email is optional
    email = models.EmailField(blank=True, default="", verbose_name="Email Address")

    # Employee Details
    employee_id = models.CharField(max_length=20, unique=True, blank=True, null=True)

    # Address (Optional)
    address = models.TextField(blank=True, null=True)

    # Status flags
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    # Timestamps
    date_joined = models.DateTimeField(default=timezone.now)
    last_login = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = CustomUserManager()

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ["-date_joined"]
        indexes = [
            models.Index(fields=["employee_id"]),
        ]
        permissions = [
            ("view_dashboard", "Can view dashboard"),
        ]

    def __str__(self):
        return f"{self.get_full_name()} ({self.phone})"

    def get_full_name(self):
        """Return the user's full name"""
        return f"{self.first_name} {self.last_name}".strip()

    def get_short_name(self):
        """Return the user's short name"""
        return self.first_name

    @property
    def is_admin(self):
        """Check if user is an administrator"""
        if self.is_superuser:
            return True
        if self.pk and self.groups.filter(name__in=["Admin", "Administrator"]).exists():
            return True
        return False

    @property
    def primary_role(self):
        """Return primary group name for display"""
        if self.is_superuser:
            return "Administrator"
        if self.pk:
            first_group = self.groups.first()
            if first_group:
                return first_group.name
        return "Staff"

    @property
    def all_roles(self):
        """Return all assigned groups as list of strings"""
        if self.pk:
            group_names = list(self.groups.values_list("name", flat=True))
            if group_names:
                return group_names
        if self.is_superuser:
            return ["Administrator"]
        return ["Staff"]

    def create_employee_id(self, save=True):
        """
        Generate and assign a unique employee ID (e.g., EMP0001).
        """
        if not self.employee_id:
            self.employee_id = generate_unique_code("EMP", CustomUser, "employee_id", 4)
            if save and self.pk:
                super(CustomUser, self).save(update_fields=["employee_id"])
        return self.employee_id

    def save(self, *args, **kwargs):
        if not self.employee_id:
            self.employee_id = generate_unique_code("EMP", CustomUser, "employee_id", 4)
        super().save(*args, **kwargs)


# # ============================================
# # USER ACTIVITY TRACKING
# # ============================================


# class UserActivity(models.Model):
#     """Track user actions for audit trail"""

#     ACTION_TYPES = [
#         ("login", "User Login"),
#         ("logout", "User Logout"),
#         ("create", "Create Record"),
#         ("update", "Update Record"),
#         ("delete", "Delete Record"),
#         ("view", "View Record"),
#         ("print", "Print Document"),
#         ("export", "Export Data"),
#     ]

#     user = models.ForeignKey(
#         User, on_delete=models.SET_NULL, null=True, related_name="activities"
#     )
#     action_type = models.CharField(max_length=20, choices=ACTION_TYPES)

#     # What was affected
#     module = models.CharField(
#         max_length=50, help_text="e.g., Customer, Job Card, Invoice"
#     )
#     record_id = models.CharField(
#         max_length=100, blank=True, null=True, help_text="ID of the affected record"
#     )

#     # Details
#     description = models.TextField(blank=True, null=True)
#     ip_address = models.GenericIPAddressField(blank=True, null=True)
#     user_agent = models.CharField(max_length=255, blank=True, null=True)

#     # Metadata
#     timestamp = models.DateTimeField(auto_now_add=True)

#     class Meta:
#         verbose_name_plural = "User Activities"
#         ordering = ["-timestamp"]
#         indexes = [
#             models.Index(fields=["user", "timestamp"]),
#             models.Index(fields=["action_type"]),
#             models.Index(fields=["module"]),
#         ]

#     def __str__(self):
#         user_name = self.user.get_full_name() if self.user else "Unknown User"
#         return f"{user_name} - {self.action_type} - {self.module} at {self.timestamp}"


# # ============================================
# # LOGIN ATTEMPTS & SECURITY
# # ============================================


# class LoginAttempt(models.Model):
#     """Track login attempts for security"""

#     phone = models.CharField(max_length=10)
#     ip_address = models.GenericIPAddressField()
#     user_agent = models.CharField(max_length=255, blank=True, null=True)

#     success = models.BooleanField(default=False)
#     failure_reason = models.CharField(max_length=100, blank=True, null=True)

#     timestamp = models.DateTimeField(auto_now_add=True)

#     class Meta:
#         ordering = ["-timestamp"]
#         indexes = [
#             models.Index(fields=["phone", "timestamp"]),
#             models.Index(fields=["ip_address", "timestamp"]),
#         ]

#     def __str__(self):
#         status = "Success" if self.success else "Failed"
#         return f"{self.phone} - {status} - {self.timestamp}"


# # ============================================
# # USER SESSIONS (Optional - for tracking active sessions)
# # ============================================


# class UserSession(models.Model):
#     """Track active user sessions"""

#     user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sessions")
#     session_key = models.CharField(max_length=40, unique=True)

#     ip_address = models.GenericIPAddressField()
#     user_agent = models.CharField(max_length=255, blank=True, null=True)
#     device_info = models.CharField(max_length=255, blank=True, null=True)

#     login_time = models.DateTimeField(auto_now_add=True)
#     last_activity = models.DateTimeField(auto_now=True)
#     logout_time = models.DateTimeField(blank=True, null=True)

#     is_active = models.BooleanField(default=True)

#     class Meta:
#         ordering = ["-login_time"]
#         indexes = [
#             models.Index(fields=["user", "is_active"]),
#             models.Index(fields=["session_key"]),
#         ]

#     def __str__(self):
#         return f"{self.user.get_full_name()} - {self.login_time}"

#     @property
#     def duration(self):
#         """Calculate session duration"""
#         if self.logout_time:
#             return self.logout_time - self.login_time
#         return timezone.now() - self.login_time

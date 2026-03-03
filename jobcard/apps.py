"""App configuration for the Job Card app."""

from django.apps import AppConfig


class JobcardConfig(AppConfig):
    """Jobcard application config."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "jobcard"

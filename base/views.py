from datetime import datetime, timedelta
from decimal import Decimal
import json

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils import timezone
from django.db.models import Sum
from django.db.models.functions import Coalesce

from jobcard.models import JobCard
from invoice.models import Invoice


def get_user_home_url(user):
    """Determine landing page based on user permissions."""
    if (
        user.is_superuser
        or getattr(user, "is_admin", False)
        or getattr(user, "is_staff", False)
        or user.has_perm("user.view_dashboard")
    ):
        return "base:home"
    if user.has_perm("jobcard.add_jobcard"):
        return "jobcard:list"
    if user.has_perm("invoice.add_invoice"):
        return "invoice:list"
    if user.has_perm("inventory.add_inventory"):
        return "inventory:list"
    if user.has_perm("jobcard.view_jobcard"):
        return "jobcard:list"
    if user.has_perm("customer.view_customer"):
        return "customer:list"
    if user.has_perm("vehicle.view_vehiclemodel"):
        return "vehicle:list"
    if user.has_perm("inventory.view_inventory"):
        return "inventory:list"
    if user.has_perm("invoice.view_invoice"):
        return "invoice:list"
    return "base:home"


def login_view(request):
    """Handle user login via phone + password."""
    # Already logged in? Go to authorized landing page
    if request.user.is_authenticated:
        return redirect(get_user_home_url(request.user))

    error = None
    phone = ""

    if request.method == "POST":
        phone = request.POST.get("phone", "").strip()
        password = request.POST.get("password", "")

        if phone and password:
            user = authenticate(request, username=phone, password=password)
            if user is not None:
                login(request, user)
                # Safely redirect to 'next' param or default landing page
                next_url = request.GET.get("next")
                if next_url and url_has_allowed_host_and_scheme(
                    url=next_url,
                    allowed_hosts={request.get_host()},
                    require_https=request.is_secure(),
                ):
                    return redirect(next_url)
                return redirect(get_user_home_url(user))
            else:
                error = "Invalid phone number or password."
        else:
            error = "Please enter both phone number and password."

    return render(request, "base/login.html", {"error": error, "phone": phone})


def logout_view(request):
    """Log the user out and redirect to login page."""
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect("base:login")


@login_required
def home_view(request):
    """Dashboard home page with live metrics, charts, and recent activity."""
    # Only superusers, admins, staff, or users with view_dashboard permission can access Dashboard
    if not (
        request.user.is_superuser
        or getattr(request.user, "is_admin", False)
        or getattr(request.user, "is_staff", False)
        or request.user.has_perm("user.view_dashboard")
    ):
        target = get_user_home_url(request.user)
        if target != "base:home":
            return redirect(target)
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied("You do not have permission to view the dashboard.")
    now = timezone.now()
    today = now.date()
    month_start = today.replace(day=1)
    week_start = now - timedelta(days=7)

    # 1. Revenue this month & last month
    revenue_this_month = (
        Invoice.objects.filter(created_at__gte=month_start).aggregate(
            total=Coalesce(Sum("total_amount"), Decimal("0"))
        )["total"]
    )

    prev_month_end = month_start - timedelta(days=1)
    prev_month_start = prev_month_end.replace(day=1)
    revenue_last_month = (
        Invoice.objects.filter(
            created_at__gte=prev_month_start, created_at__lte=prev_month_end
        ).aggregate(total=Coalesce(Sum("total_amount"), Decimal("0")))["total"]
    )

    revenue_growth = 0
    if revenue_last_month > 0:
        revenue_growth = round(
            float((revenue_this_month - revenue_last_month) / revenue_last_month * 100),
            1,
        )

    # 2. Operational KPIs
    jobcards_today = JobCard.objects.filter(created_at__date=today).count()
    yesterday = today - timedelta(days=1)
    jobcards_yesterday = JobCard.objects.filter(created_at__date=yesterday).count()
    jobcards_today_diff = jobcards_today - jobcards_yesterday

    vehicles_in_workshop = JobCard.objects.filter(
        status__in=[JobCard.Status.PENDING, JobCard.Status.IN_PROGRESS]
    ).count()

    pending_jobs = JobCard.objects.filter(status=JobCard.Status.PENDING).count()
    in_progress_jobs = JobCard.objects.filter(status=JobCard.Status.IN_PROGRESS).count()
    completed_jobs = JobCard.objects.filter(status=JobCard.Status.COMPLETED).count()

    completed_this_week = JobCard.objects.filter(
        status=JobCard.Status.COMPLETED,
        completed_at__gte=week_start,
    ).count()

    # 3. Recent job cards
    recent_jobcards = (
        JobCard.objects.all()
        .select_related("customer", "vehicle_model", "vehicle_model__make")
        .order_by("-created_at")[:6]
    )

    # 4. Monthly Revenue (last 6 months) for Chart.js
    revenue_labels = []
    revenue_values = []
    for i in range(5, -1, -1):
        m = (now.month - 1 - i) % 12 + 1
        y = now.year + ((now.month - 1 - i) // 12)
        m_start = datetime(y, m, 1)
        if m == 12:
            m_end = datetime(y + 1, 1, 1)
        else:
            m_end = datetime(y, m + 1, 1)

        m_name = m_start.strftime("%b")
        m_rev = Invoice.objects.filter(
            created_at__gte=m_start, created_at__lt=m_end
        ).aggregate(total=Coalesce(Sum("total_amount"), Decimal("0")))["total"]

        revenue_labels.append(m_name)
        revenue_values.append(float(m_rev))

    context = {
        "today_display": now.strftime("%A, %d %b %Y"),
        "revenue_this_month": revenue_this_month,
        "revenue_last_month": revenue_last_month,
        "revenue_growth": revenue_growth,
        "jobcards_today": jobcards_today,
        "jobcards_today_diff": jobcards_today_diff,
        "vehicles_in_workshop": vehicles_in_workshop,
        "pending_jobs": pending_jobs,
        "in_progress_jobs": in_progress_jobs,
        "completed_jobs": completed_jobs,
        "completed_this_week": completed_this_week,
        "recent_jobcards": recent_jobcards,
        "revenue_chart_labels": json.dumps(revenue_labels),
        "revenue_chart_data": json.dumps(revenue_values),
        "status_chart_data": json.dumps([pending_jobs, in_progress_jobs, completed_jobs]),
    }

    return render(request, "base/home.html", context)

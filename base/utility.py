from django.core.validators import RegexValidator
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.template.loader import render_to_string

phone_regex = RegexValidator(
    regex=r"^\d{10}$",
    message="Phone number must be exactly 10 digits",
)


def render_paginated_response(
    request,
    queryset,
    table_template,
    per_page=20,
    pagination_template="common/_pagination.html",
    **kwargs,
):
    """
    Reusable pagination + HTML rendering helper for HTMX/AJAX.

    Args:
        request: Django request object
        queryset: List/QuerySet to paginate
        table_template: Path to table HTML template
        per_page: Number of items per page
        pagination_template: Path to pagination template (optional)
        **kwargs: Additional context variables to pass to template

    Returns:
        JsonResponse with HTML table + pagination
    """
    paginator = Paginator(queryset, per_page)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "total_count": paginator.count,
    }
    # Merge additional context from kwargs
    context.update(kwargs)

    # Render table
    table_html = render_to_string(table_template, context, request=request)

    # Render pagination if needed
    pagination_html = ""
    if page_obj and page_obj.paginator.num_pages > 1:
        pagination_html = render_to_string(
            pagination_template, context, request=request
        )

    return JsonResponse(
        {
            "html": table_html,
            "pagination": pagination_html,
            "success": True,
        }
    )


def table_sorting(request, valid_sorts=None, default_sort="-id"):
    """
    Generalized sorting helper for multi-column sort.
    """
    is_mapping = isinstance(valid_sorts, dict)
    if valid_sorts is None:
        valid_keys = set()
    elif is_mapping:
        valid_keys = set(valid_sorts.keys())
    else:
        valid_keys = set(valid_sorts)

    sort_param = request.GET.get("sort", "")
    if not sort_param:
        return [default_sort]

    sort_fields = [f.strip() for f in sort_param.split(",") if f.strip()]
    final_sorts = []

    for field in sort_fields:
        is_desc = field.startswith("-")
        clean_field = field.lstrip("-")

        if clean_field in valid_keys:
            if is_mapping:
                # Get the DB field from the map
                db_field = valid_sorts[clean_field]
                # Apply direction to the DB field
                if is_desc:
                    final_sorts.append(f"-{db_field}")
                else:
                    final_sorts.append(db_field)
            else:
                final_sorts.append(field)

    if not final_sorts:
        return [default_sort]

    return final_sorts

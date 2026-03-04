import re
import logging
from django.core.cache import cache
from django.core.cache.backends.base import InvalidCacheBackendError
from django.http import JsonResponse
from inventory.models import Inventory
from vehicle.models import VehicleModel
from customer.models import Customer
from jobcard.models import JobCard
from invoice.models import Invoice
from rapidfuzz import process, fuzz

logger = logging.getLogger(__name__)
TOKENIZER = re.compile(r"[a-zA-Z0-9]+")

INVENTORY_SEARCH_FIELDS = [
    "name",
    "part_number",
    "barcode",
    "brand",
    "category__name",
    "compatible_vehicles__model_name",
    "compatible_vehicles__make__name",
]

VEHICLE_SEARCH_FIELDS = [
    "make__name",
    "model_name",
    "fuel_type",
    "transmission",
]

CUSTOMER_SEARCH_FIELDS = [
    "name",
    "phone",
    "address",
]

JOB_CARD_SEARCH_FIELDS = [
    "job_card_number",
    "customer__name",
    "customer__phone",
    "vehicle_model__make__name",
    "vehicle_model__model_name",
    "vehicle_number",
]

INVOICE_SEARCH_FIELDS = [
    "invoice_number",
    "customer__name",
    "customer__phone",
    "job_card__job_card_number",
]


def get_instance_tokens(instance, fields):
    """
    Helper to extract tokens from a single model instance.
    Used by signals to check if cache invalidation is actually needed.
    """
    tokens = set()
    for field_path in fields:
        # Handle related fields (e.g., 'customer__name')
        value = instance
        parts = field_path.split("__")
        try:
            for part in parts:
                if value is None:
                    break
                value = getattr(value, part)
        except AttributeError:
            continue  # Field might not exist or be accessible

        if value:
            # Tokenize
            found = TOKENIZER.findall(str(value).lower())
            tokens.update(t for t in found if len(t) > 2)
    return tokens


def get_related_words(query, list_of_words, limit=10, score_cutoff=60):
    """
    Returns top fuzzy-matched words for a query.
    - Uses rapidfuzz for speed.
    - Avoids redundant deduplication.
    - Limits results early for efficiency.
    """

    if not query or len(query) < 2 or not list_of_words:
        return []

    # rapidfuzz can handle iterables directly (no need to force list)
    matches = process.extract(
        query.lower(),
        list_of_words,
        scorer=fuzz.WRatio,
        limit=limit,
        score_cutoff=score_cutoff,
    )

    # Extract only words (discard scores)
    return [word for word, score, _ in matches]


def get_search_words(
    query,
    model,
    fields,
    cache_key,
    cache_timeout=3600,
    max_words=50000,
):
    """
    Optimized helper to build/search word lists from model fields.
    - Uses Redis/DB cache to avoid rebuilding.
    - Minimizes memory overhead by streaming.
    - Tokenizes with set comprehension instead of nested loops.
    - Limits max_words to avoid huge cache payloads.
    - Handles cache connection errors gracefully.
    """

    # 1. Try cache first (Redis-compatible)
    try:
        searchable_items = cache.get(cache_key)
        if searchable_items is not None:
            return get_related_words(query, searchable_items)
    except (InvalidCacheBackendError, ConnectionError, TimeoutError) as e:
        # Redis might be down or misconfigured - log and continue without cache
        logger.warning(
            f"Cache read failed for key '{cache_key}': {e}. Proceeding without cache."
        )

    # 2. Stream from DB efficiently (iterator avoids full memory load)
    queryset = model.objects.values_list(*fields).distinct().iterator()

    all_words = set()
    for row in queryset:
        # Flatten row → tokenize in one go
        tokens = {
            token
            for field in row
            if field
            for token in TOKENIZER.findall(str(field).lower())
            if len(token) > 2
        }
        all_words.update(tokens)

        # Optional: early cutoff if dataset is massive
        if len(all_words) >= max_words:
            break

    # 3. Convert to list once
    searchable_items = list(all_words)

    # 4. Save in cache (Redis-compatible - Django handles serialization)
    try:
        cache.set(cache_key, searchable_items, cache_timeout)
    except (InvalidCacheBackendError, ConnectionError, TimeoutError) as e:
        # Redis might be down - log but don't fail the request
        logger.warning(
            f"Cache write failed for key '{cache_key}': {e}. Results returned without caching."
        )

    # 5. Get suggestions
    return get_related_words(query, searchable_items)


def inventory_all_suggestions(request):

    query = request.GET.get("q", "").strip()

    if not query or len(query) < 2:
        return JsonResponse({"success": True, "data": []})

    suggestions = get_search_words(
        query=query,
        model=Inventory,
        fields=INVENTORY_SEARCH_FIELDS,
        cache_key="inventory_search_words",
    )

    return JsonResponse({"success": True, "data": suggestions})


def vehicle_all_suggestions(request):

    query = request.GET.get("q", "").strip()

    if not query or len(query) < 2:
        return JsonResponse({"success": True, "data": []})

    suggestions = get_search_words(
        query=query,
        model=VehicleModel,
        fields=VEHICLE_SEARCH_FIELDS,
        cache_key="vehicle_search_words",
    )

    return JsonResponse({"success": True, "data": suggestions})


def customer_all_suggestions(request):

    query = request.GET.get("q", "").strip()

    if not query or len(query) < 2:
        return JsonResponse({"success": True, "data": []})

    suggestions = get_search_words(
        query=query,
        model=Customer,
        fields=CUSTOMER_SEARCH_FIELDS,
        cache_key="customer_search_words",
    )

    return JsonResponse({"success": True, "data": suggestions})


def jobcard_all_suggestions(request):

    query = request.GET.get("q", "").strip()

    if not query or len(query) < 2:
        return JsonResponse({"success": True, "data": []})

    suggestions = get_search_words(
        query=query,
        model=JobCard,
        fields=JOB_CARD_SEARCH_FIELDS,
        cache_key="jobcard_search_words",
    )

    return JsonResponse({"success": True, "data": suggestions})


def invoice_all_suggestions(request):

    query = request.GET.get("q", "").strip()

    if not query or len(query) < 2:
        return JsonResponse({"success": True, "data": []})

    suggestions = get_search_words(
        query=query,
        model=Invoice,
        fields=INVOICE_SEARCH_FIELDS,
        cache_key="invoice_search_words",
    )

    return JsonResponse({"success": True, "data": suggestions})

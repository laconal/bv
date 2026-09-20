from django.db import models as django_models
from rest_framework.exceptions import ValidationError

_COMPARISON_LOOKUPS = {"eq": "exact", "gt": "gt", "gte": "gte", "lt": "lt", "lte": "lte"}

# created_at/updated_at are housekeeping timestamps (auto_now_add/auto_now on
# TimestampedModel) - filtering on them compares by calendar date only, not
# time-of-day, via Django's `__date` lookup transform. Business-domain
# datetime fields (e.g. a discount's starts_at/ends_at) are NOT in this set
# and keep full datetime precision.
_DATE_ONLY_FIELDS = {"created_at", "updated_at"}


def apply_filters(queryset, filters: dict | None):
    """
    Generic filter dict -> queryset, driven by `model.ALLOWED_FILTERS` (a
    `set[str]` of field names each model opts into, mirroring the old
    backend's `ALLOWED_FILTERS`/`apply_dynamic_filters`). Unknown field names
    are silently ignored (frontend can send a superset without erroring);
    an unsupported operator inside a filter value raises 400.

    Filter value shapes per field, keyed by field name:
      - plain value on a text field (Char/Text/Slug, no choices) -> icontains
      - plain value otherwise -> exact match
      - list -> `__in`
      - {"eq"|"gt"|"gte"|"lt"|"lte": value} -> comparison (numeric/date fields)
    """
    if not filters:
        return queryset

    model = queryset.model
    allowed = getattr(model, "ALLOWED_FILTERS", set())
    lookups: dict = {}
    touches_m2m = False

    for field_name, value in filters.items():
        if field_name not in allowed or value is None:
            continue

        field = model._meta.get_field(field_name)
        if field.many_to_many:
            touches_m2m = True

        lookup_base = f"{field_name}__date" if field_name in _DATE_ONLY_FIELDS else field_name

        if isinstance(value, dict):
            for op, op_value in value.items():
                if op not in _COMPARISON_LOOKUPS:
                    raise ValidationError(
                        {field_name: f"Unsupported operator '{op}'. Use one of: eq, gt, gte, lt, lte."}
                    )
                if op_value is not None:
                    lookups[f"{lookup_base}__{_COMPARISON_LOOKUPS[op]}"] = op_value
            continue

        if isinstance(value, list):
            lookups[f"{lookup_base}__in"] = value
        elif isinstance(value, str) and isinstance(field, (django_models.CharField, django_models.TextField)) \
                and not field.choices:
            lookups[f"{field_name}__icontains"] = value
        else:
            lookups[lookup_base] = value

    queryset = queryset.filter(**lookups)
    return queryset.distinct() if touches_m2m else queryset

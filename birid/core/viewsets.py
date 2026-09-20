from drf_spectacular.utils import OpenApiExample, extend_schema, extend_schema_view
from rest_framework import exceptions, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.filtering import apply_filters
from core.pagination import paginate_body
from core.serializers import GetAllRequestSerializer

# created_at/updated_at compare by calendar date only (see core/filtering.py)
# - reused across every resource's filters_example so that's obvious in the
# example itself, not just the field's help_text.
CREATED_AT_FILTER_EXAMPLE = {
    "eq": "2026-09-21",
    "gt": "2026-01-01",
    "gte": "2026-01-01",
    "lt": "2026-12-31",
    "lte": "2026-12-31",
}


class NoPutModelViewSet(viewsets.ModelViewSet):
    """
    ModelViewSet without full-update PUT (only partial-update PATCH), and
    with GET .../ (list) replaced by POST .../get-all: filters can get large
    (see core/filtering.py), and those belong in a body, not a query string.
    """

    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    @extend_schema(exclude=True)
    def list(self, request, *args, **kwargs):
        raise exceptions.MethodNotAllowed("GET", detail="List via POST .../get-all instead.")

    @action(detail=False, methods=["post"], url_path="get-all")
    def get_all(self, request, *args, **kwargs):
        filters = request.data.get("filters") or {}
        queryset = apply_filters(self.get_queryset(), filters)
        result = paginate_body(queryset, request.data.get("page"), request.data.get("pageSize"))
        serializer = self.get_serializer(result["items"], many=True)
        return Response({
            "items": serializer.data,
            "page": result["page"],
            "totalPages": result["totalPages"],
            "total": result["total"],
        })


def paginated_serializer(item_serializer_class):
    """
    {items: [<item_serializer_class>], page, totalPages, total} - matches
    core/pagination.py's shape exactly. Any body-driven list endpoint bypasses
    DRF's own pagination classes (page/pageSize come from the POST body, not
    query params - see core/pagination.paginate_body), so drf-spectacular
    can't auto-derive this response shape the way it does for a standard
    paginated list() action; it has to be spelled out explicitly per resource.
    Public - reused outside this module wherever a body-paginated endpoint
    isn't a full ModelViewSet (e.g. buyers/views.py's favorites lists).
    """
    name = f"Paginated{item_serializer_class.__name__}"
    return type(name, (serializers.Serializer,), {
        "__module__": __name__,
        "items": item_serializer_class(many=True),
        "page": serializers.IntegerField(),
        "totalPages": serializers.IntegerField(),
        "total": serializers.IntegerField(),
    })


def tagged(tag: str, serializer_class, filters_example: dict | None = None):
    """
    Puts every CRUD action of a viewset (get_all included) under one explicit
    Swagger tag, and documents get_all's actual response shape (see
    _paginated_serializer - without this it falls back to describing get_all
    as returning one bare `serializer_class` instance, not the paginated
    envelope it actually returns).

    Pass `filters_example` (a realistic `filters` dict for that resource,
    matching its ALLOWED_FILTERS) to show a concrete example request body -
    Swagger otherwise has no way to know `filters` is a free-form dict whose
    keys/value-shapes depend on which resource this is.
    """
    scoped = extend_schema(tags=[tag])

    get_all_kwargs = {
        "tags": [tag],
        "request": GetAllRequestSerializer,
        "responses": paginated_serializer(serializer_class),
        "summary": "List (filterable)",
    }
    if filters_example is not None:
        get_all_kwargs["examples"] = [
            OpenApiExample(
                "Example",
                value={"page": 1, "pageSize": 20, "filters": filters_example},
                request_only=True,
            ),
        ]
    get_all_scoped = extend_schema(**get_all_kwargs)

    return extend_schema_view(
        create=scoped, retrieve=scoped, update=scoped, partial_update=scoped, destroy=scoped,
        get_all=get_all_scoped,
    )

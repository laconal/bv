from collections import OrderedDict

from django.core.paginator import EmptyPage, Paginator
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


class DefaultPagination(PageNumberPagination):
    page_query_param = "page"
    page_size_query_param = "pageSize"
    page_size = DEFAULT_PAGE_SIZE
    max_page_size = MAX_PAGE_SIZE

    def get_paginated_response(self, data):
        return Response(OrderedDict([
            ("items", data),
            ("page", self.page.number),
            ("totalPages", self.page.paginator.num_pages),
            ("total", self.page.paginator.count),
        ]))

    def get_paginated_response_schema(self, schema):
        return {
            "type": "object",
            "properties": {
                "items": {"type": "array", "items": schema},
                "page": {"type": "integer", "example": 1},
                "totalPages": {"type": "integer", "example": 5},
                "total": {"type": "integer", "example": 100},
            },
        }


def paginate_body(queryset, page, page_size) -> dict:
    """
    Same page/pageSize/items/totalPages/total contract as DefaultPagination,
    but reading page/pageSize from an already-parsed value (the POST body of
    a `.../get-all` action) instead of query params - DRF's pagination
    classes are hardwired to request.query_params, so a body-driven list
    endpoint can't reuse them directly.
    """
    page = page if page is not None else 1
    page_size = page_size if page_size is not None else DEFAULT_PAGE_SIZE

    if not isinstance(page, int) or page < 1:
        raise ValidationError({"page": "Must be an integer >= 1."})
    if not isinstance(page_size, int) or not (1 <= page_size <= MAX_PAGE_SIZE):
        raise ValidationError({"pageSize": f"Must be an integer between 1 and {MAX_PAGE_SIZE}."})

    paginator = Paginator(queryset, page_size)
    try:
        page_obj = paginator.page(page)
    except EmptyPage:
        raise NotFound("Invalid page.")

    return {
        "items": list(page_obj.object_list),
        "page": page,
        "totalPages": paginator.num_pages,
        "total": paginator.count,
    }

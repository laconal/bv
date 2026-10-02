from django.db.models import Prefetch
from drf_spectacular.utils import extend_schema, extend_schema_view

from core.viewsets import CREATED_AT_FILTER_EXAMPLE, tagged
from products.models import StoreProduct
from stores.viewsets import StoreScopedModelViewSet

from .models import StoreNews
from .serializers import StoreNewsResponseSerializer, StoreNewsSerializer


@extend_schema_view(
    # StoreNewsSerializer.image is write_only with its read shape injected
    # by to_representation() - not visible to static schema analysis (see
    # StoreNewsResponseSerializer's docstring).
    retrieve=extend_schema(responses=StoreNewsResponseSerializer),
    create=extend_schema(responses=StoreNewsResponseSerializer),
    update=extend_schema(responses=StoreNewsResponseSerializer),
    partial_update=extend_schema(responses=StoreNewsResponseSerializer),
)
@tagged("stores-news", StoreNewsResponseSerializer, filters_example={
    "title": "Скидки к сезону",
    "news_type": "discount",
    "status": "active",
    "created_at": CREATED_AT_FILTER_EXAMPLE,
})
class StoreNewsViewSet(StoreScopedModelViewSet):
    queryset = StoreNews.objects.prefetch_related(
        Prefetch("products", queryset=StoreProduct.objects.only("id")), "image__renditions",
    )
    serializer_class = StoreNewsSerializer

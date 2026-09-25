from django.db.models import Prefetch

from core.viewsets import CREATED_AT_FILTER_EXAMPLE, tagged
from products.models import StoreProduct
from stores.viewsets import StoreScopedModelViewSet

from .models import StoreNews
from .serializers import StoreNewsSerializer


@tagged("stores-news", StoreNewsSerializer, filters_example={
    "title": "Скидки к сезону",
    "news_type": "discount",
    "status": "active",
    "created_at": CREATED_AT_FILTER_EXAMPLE,
})
class StoreNewsViewSet(StoreScopedModelViewSet):
    queryset = StoreNews.objects.prefetch_related(Prefetch("products", queryset=StoreProduct.objects.only("id")))
    serializer_class = StoreNewsSerializer

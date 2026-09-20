from core.viewsets import CREATED_AT_FILTER_EXAMPLE, tagged
from stores.viewsets import StoreScopedModelViewSet

from .models import StoreNews
from .serializers import StoreNewsSerializer


@tagged("store-admin-news", StoreNewsSerializer, filters_example={
    "title": "Скидки к сезону",
    "news_type": "discount",
    "status": "active",
    "created_at": CREATED_AT_FILTER_EXAMPLE,
})
class StoreNewsViewSet(StoreScopedModelViewSet):
    queryset = StoreNews.objects.all()
    serializer_class = StoreNewsSerializer

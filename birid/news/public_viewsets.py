from django.db.models import Prefetch
from django.utils import timezone
from rest_framework.permissions import AllowAny

from core.viewsets import CREATED_AT_FILTER_EXAMPLE, PublicReadOnlyViewSet, public_tagged
from products.models import StoreProduct

from .models import NewsStatus, StoreNews
from .serializers import PublicStoreNewsSerializer


@public_tagged("public-news", PublicStoreNewsSerializer, filters_example={
    "store": 1,
    "title": "Скидки к сезону",
    "news_type": "discount",
    "created_at": CREATED_AT_FILTER_EXAMPLE,
})
class PublicStoreNewsViewSet(PublicReadOnlyViewSet):
    """
    Unauthenticated marketplace browsing - only news that is currently
    "live": status=active (excludes draft/archived), the current moment
    falls inside [starts_at, ends_at], and the owning store is active.
    """

    authentication_classes = []
    permission_classes = [AllowAny]
    serializer_class = PublicStoreNewsSerializer

    def get_queryset(self):
        now = timezone.now()
        return StoreNews.objects.filter(
            store__active=True, status=NewsStatus.ACTIVE, starts_at__lte=now, ends_at__gte=now,
        ).prefetch_related(Prefetch("products", queryset=StoreProduct.objects.only("id")))

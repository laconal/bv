from buyers.authentication import BuyerJWTAuthentication
from django.db.models import F, Q
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from core.viewsets import CREATED_AT_FILTER_EXAMPLE, PublicReadOnlyViewSet, public_tagged

from .discounts import prefetch_active_discounts
from .models import StoreProduct, StoreProductView
from .serializers import PRODUCT_PREFETCH, PublicProductSerializer, with_favorites_count


@public_tagged("public-products", PublicProductSerializer, filters_example={
    "store": 1,
    "name": "Платье",
    "category": 1,
    "subcategory": 2,
    "brand": "Zara",
    "manufacture": "Италия",
    "materials": [1, 2],
    "tags": [1, 2],
    "color": 3,
    "size": [40, 42],
    "price_sale": {"gte": "1000.00", "lte": "20000.00"},
    "price_rental": {"gte": "0.00"},
    "price_tailoring": {"gte": "0.00"},
    "is_sellable": True,
    "is_rentable": False,
    "blur_image_in_site": False,
    "created_at": CREATED_AT_FILTER_EXAMPLE,
})
class PublicProductViewSet(PublicReadOnlyViewSet):
    """
    Unauthenticated marketplace browsing - only products belonging to an
    active store are visible. BuyerJWTAuthentication is attached (with
    AllowAny) so a buyer token is recognized when present but never
    required - anonymous browsing still works, it's just the view-count
    increment on retrieve that needs to know who's asking.
    """

    authentication_classes = [BuyerJWTAuthentication]
    permission_classes = [AllowAny]
    serializer_class = PublicProductSerializer

    def get_queryset(self):
        return with_favorites_count(
            StoreProduct.objects.filter(store__active=True, category__visible=True)
            .filter(Q(subcategory__isnull=True) | Q(subcategory__visible=True))
            .prefetch_related(*PRODUCT_PREFETCH, prefetch_active_discounts())
        )

    def retrieve(self, request, *args, **kwargs):
        return self._retrieve(request, self.get_object())

    @extend_schema(tags=["public-products"], responses=PublicProductSerializer, summary="Retrieve by slug")
    @action(detail=False, methods=["get"], url_path=r"by-slug/(?P<slug>[-a-zA-Z0-9_]+)")
    def by_slug(self, request, slug=None):
        return self._retrieve(request, get_object_or_404(self.get_queryset(), slug=slug))

    def _retrieve(self, request, instance):
        if request.user and request.user.is_authenticated:
            StoreProduct.objects.filter(id=instance.id).update(views=F("views") + 1)
            StoreProductView.objects.create(store_id=instance.store_id, product=instance)
            instance.refresh_from_db(fields=["views"])
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

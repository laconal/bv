from buyers.authentication import BuyerJWTAuthentication
from django.db.models import F
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from core.viewsets import CREATED_AT_FILTER_EXAMPLE, PublicReadOnlyViewSet, public_tagged

from .models import StoreProduct, StoreProductView
from .serializers import PublicProductSerializer


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
    "size": {"gte": 40, "lte": 46},
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
        return StoreProduct.objects.filter(store__active=True)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        if request.user and request.user.is_authenticated:
            StoreProduct.objects.filter(id=instance.id).update(views=F("views") + 1)
            StoreProductView.objects.create(store_id=instance.store_id, product=instance)
            instance.refresh_from_db(fields=["views"])
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

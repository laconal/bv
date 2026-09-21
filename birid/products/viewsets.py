from django.http import FileResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework.decorators import action

from core.viewsets import CREATED_AT_FILTER_EXAMPLE, tagged
from stores.viewsets import StoreScopedModelViewSet

from .models import (
    PhotoProcessingStatus,
    StoreCategory,
    StoreDiscount,
    StoreProduct,
    StoreProductPhoto,
    StoreProductVariant,
    StoreTag,
)
from .serializers import (
    StoreCategorySerializer,
    StoreDiscountSerializer,
    StoreProductPhotoSerializer,
    StoreProductResponseSerializer,
    StoreProductSerializer,
    StoreProductVariantSerializer,
    StoreTagSerializer,
)
from .tasks import generate_photo_renditions, process_category_cover


@tagged("stores-categories", StoreCategorySerializer, filters_example={
    "name": "Платья",
    "parent": 1,
    "created_at": CREATED_AT_FILTER_EXAMPLE,
})
class StoreCategoryViewSet(StoreScopedModelViewSet):
    queryset = StoreCategory.objects.all()
    serializer_class = StoreCategorySerializer

    def perform_create(self, serializer):
        has_cover = bool(serializer.validated_data.get("cover"))
        status = PhotoProcessingStatus.PENDING if has_cover else None
        category = serializer.save(store=self.request.user.store, cover_processing_status=status)
        if has_cover:
            process_category_cover.delay(category.id)

    def perform_update(self, serializer):
        new_cover_provided = bool(serializer.validated_data.get("cover"))
        extra = {"cover_processing_status": PhotoProcessingStatus.PENDING} if new_cover_provided else {}
        category = serializer.save(**extra)
        if new_cover_provided:
            process_category_cover.delay(category.id)


@tagged("stores-tags", StoreTagSerializer, filters_example={
    "name": "Новинка",
    "created_at": CREATED_AT_FILTER_EXAMPLE,
})
class StoreTagViewSet(StoreScopedModelViewSet):
    queryset = StoreTag.objects.all()
    serializer_class = StoreTagSerializer


@extend_schema_view(
    # StoreProductSerializer.variants is write_only with its read shape injected
    # by to_representation() - not visible to static schema analysis. Layered
    # on top of @tagged so this doesn't disturb its tags/summary, just fixes
    # up the response schema for the one field that needs it (see
    # StoreProductResponseSerializer's docstring).
    retrieve=extend_schema(responses=StoreProductResponseSerializer),
    create=extend_schema(responses=StoreProductResponseSerializer),
    update=extend_schema(responses=StoreProductResponseSerializer),
    partial_update=extend_schema(responses=StoreProductResponseSerializer),
)
@tagged("stores-products", StoreProductResponseSerializer, filters_example={
    "name": "Платье",
    "category": 1,
    "subcategory": 2,
    "brand": "Zara",
    "manufacture": "Италия",
    "material": "Хлопок",
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
class StoreProductViewSet(StoreScopedModelViewSet):
    queryset = StoreProduct.objects.all()
    serializer_class = StoreProductSerializer


@tagged("stores-product-variants", StoreProductVariantSerializer, filters_example={
    "product": 5,
    "created_at": CREATED_AT_FILTER_EXAMPLE,
})
class StoreProductVariantViewSet(StoreScopedModelViewSet):
    queryset = StoreProductVariant.objects.all()
    serializer_class = StoreProductVariantSerializer


@tagged("stores-discounts", StoreDiscountSerializer, filters_example={
    "title": "Осенняя скидка",
    "starts_at": {"gte": "2026-10-01T00:00:00Z"},
    "ends_at": {"lte": "2026-10-31T23:59:59Z"},
    "status": "active",
    "created_at": CREATED_AT_FILTER_EXAMPLE,
})
class StoreDiscountViewSet(StoreScopedModelViewSet):
    queryset = StoreDiscount.objects.all()
    serializer_class = StoreDiscountSerializer


@tagged("stores-product-photos", StoreProductPhotoSerializer, filters_example={
    "original_filename": "photo.jpg",
    "processing_status": "ready",
    "created_at": CREATED_AT_FILTER_EXAMPLE,
})
class StoreProductPhotoViewSet(StoreScopedModelViewSet):
    queryset = StoreProductPhoto.objects.all()
    serializer_class = StoreProductPhotoSerializer

    def perform_create(self, serializer):
        photo = serializer.save(store=self.request.user.store)
        generate_photo_renditions.delay(photo.id)

    @extend_schema(
        tags=["stores-product-photos"],
        responses={200: OpenApiTypes.BINARY},
        summary="Download photo file",
    )
    @action(detail=True, methods=["get"], url_path="download")
    def download(self, request, pk=None):
        photo = self.get_object()
        photo.image.open("rb")
        return FileResponse(
            photo.image,
            filename=photo.original_filename or str(photo.uuid),
            as_attachment=True,
        )

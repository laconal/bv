from rest_framework.routers import DefaultRouter

from .viewsets import (
    StoreCategoryViewSet,
    StoreDiscountViewSet,
    StoreProductPhotoViewSet,
    StoreProductVariantViewSet,
    StoreProductViewSet,
    StoreTagViewSet,
)

router = DefaultRouter()
router.register("categories", StoreCategoryViewSet, basename="store-category")
router.register("tags", StoreTagViewSet, basename="store-tag")
router.register("products", StoreProductViewSet, basename="store-product")
router.register("product-variants", StoreProductVariantViewSet, basename="store-product-variant")
router.register("product-photos", StoreProductPhotoViewSet, basename="store-product-photo")
router.register("discounts", StoreDiscountViewSet, basename="store-discount")

urlpatterns = router.urls

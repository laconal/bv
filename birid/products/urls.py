from rest_framework.routers import SimpleRouter

from .viewsets import (
    StoreCategoryViewSet,
    StoreDiscountViewSet,
    StoreProductMaterialCategoryViewSet,
    StoreProductMaterialViewSet,
    StoreProductPhotoViewSet,
    StoreProductVariantViewSet,
    StoreProductViewSet,
    StoreTagViewSet,
)

router = SimpleRouter()
router.register("categories", StoreCategoryViewSet, basename="store-category")
router.register("tags", StoreTagViewSet, basename="store-tag")
router.register(
    "product-material-categories", StoreProductMaterialCategoryViewSet, basename="store-product-material-category",
)
router.register("product-materials", StoreProductMaterialViewSet, basename="store-product-material")
router.register("products", StoreProductViewSet, basename="store-product")
router.register("product-variants", StoreProductVariantViewSet, basename="store-product-variant")
router.register("product-photos", StoreProductPhotoViewSet, basename="store-product-photo")
router.register("discounts", StoreDiscountViewSet, basename="store-discount")

urlpatterns = router.urls

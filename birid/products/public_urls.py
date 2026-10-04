from rest_framework.routers import SimpleRouter

from .public_viewsets import PublicProductViewSet, PublicStoreCategoryViewSet

router = SimpleRouter()
router.register("products", PublicProductViewSet, basename="public-product")
# Nested under the store, but the store viewset lives in stores/ and doesn't own this
# route, so the prefix carries the store_pk regex directly.
router.register(
    r"stores/(?P<store_pk>\d+)/categories", PublicStoreCategoryViewSet, basename="public-store-category",
)

urlpatterns = router.urls

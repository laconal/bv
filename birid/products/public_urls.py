from rest_framework.routers import SimpleRouter

from .public_viewsets import PublicProductViewSet

router = SimpleRouter()
router.register("products", PublicProductViewSet, basename="public-product")

urlpatterns = router.urls

from rest_framework.routers import SimpleRouter

from .public_viewsets import PublicStoreViewSet

router = SimpleRouter()
router.register("stores", PublicStoreViewSet, basename="public-store")

urlpatterns = router.urls

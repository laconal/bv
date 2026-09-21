from rest_framework.routers import SimpleRouter

from .public_viewsets import PublicStoreNewsViewSet

router = SimpleRouter()
router.register("news", PublicStoreNewsViewSet, basename="public-news")

urlpatterns = router.urls

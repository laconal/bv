from rest_framework.routers import SimpleRouter

from .viewsets import StoreNewsViewSet

router = SimpleRouter()
router.register("news", StoreNewsViewSet, basename="store-news")

urlpatterns = router.urls

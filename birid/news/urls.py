from rest_framework.routers import DefaultRouter

from .viewsets import StoreNewsViewSet

router = DefaultRouter()
router.register("news", StoreNewsViewSet, basename="store-news")

urlpatterns = router.urls

from rest_framework.routers import SimpleRouter

from .viewsets import StoreOrderViewSet

router = SimpleRouter()
router.register("orders", StoreOrderViewSet, basename="store-order")

urlpatterns = router.urls

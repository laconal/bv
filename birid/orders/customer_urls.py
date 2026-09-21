from rest_framework.routers import SimpleRouter

from .customer_viewsets import CustomerOrderViewSet

router = SimpleRouter()
router.register("orders", CustomerOrderViewSet, basename="customer-order")

urlpatterns = router.urls

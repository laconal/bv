from django.urls import path
from rest_framework.routers import DefaultRouter

from .store_views import StoreView
from .viewsets import (
    IconViewSet,
    StoreAddressViewSet,
    StoreColorViewSet,
    StoreContactViewSet,
    StoreServiceViewSet,
    StoreSocialLinkViewSet,
)

router = DefaultRouter()
router.register("social-links", StoreSocialLinkViewSet, basename="store-social-link")
router.register("addresses", StoreAddressViewSet, basename="store-address")
router.register("contacts", StoreContactViewSet, basename="store-contact")
router.register("services", StoreServiceViewSet, basename="store-service")
router.register("colors", StoreColorViewSet, basename="store-color")
router.register("icons", IconViewSet, basename="icon")

urlpatterns = [
    path("store", StoreView.as_view(), name="store-profile"),
] + router.urls

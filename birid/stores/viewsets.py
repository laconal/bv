from rest_framework.permissions import IsAuthenticated

from core.viewsets import CREATED_AT_FILTER_EXAMPLE, NoPutModelViewSet, tagged

from .authentication import StoreAdminJWTAuthentication
from .models import Icon, StoreAddress, StoreColor, StoreContact, StoreService, StoreSocialLink
from .serializers import (
    IconSerializer,
    StoreAddressSerializer,
    StoreColorSerializer,
    StoreContactSerializer,
    StoreServiceSerializer,
    StoreSocialLinkSerializer,
)


class StoreScopedModelViewSet(NoPutModelViewSet):
    """
    CRUD scoped to the authenticated store admin's own store. `store` is never
    read from the request body/URL - only from the JWT-resolved account - so
    one store's admin can never read, edit, or delete another store's rows,
    and a foreign id 404s instead of leaking existence.
    """

    authentication_classes = [StoreAdminJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return super().get_queryset().filter(store=self.request.user.store)

    def perform_create(self, serializer):
        serializer.save(store=self.request.user.store)


@tagged("store-admin-social-links", StoreSocialLinkSerializer, filters_example={
    "platform": "instagram",
    "nickname": "store1_ig",
    "visible": True,
    "created_at": CREATED_AT_FILTER_EXAMPLE,
})
class StoreSocialLinkViewSet(StoreScopedModelViewSet):
    queryset = StoreSocialLink.objects.all()
    serializer_class = StoreSocialLinkSerializer


@tagged("store-admin-addresses", StoreAddressSerializer, filters_example={
    "name": "Главный офис",
    "address": "ул. Ленина, 1",
    "landmark": "рядом с ТЦ Атриум",
    "working_hours": "09:00-21:00",
    "phone": "+79990001122",
    "created_at": CREATED_AT_FILTER_EXAMPLE,
})
class StoreAddressViewSet(StoreScopedModelViewSet):
    queryset = StoreAddress.objects.all()
    serializer_class = StoreAddressSerializer


@tagged("store-admin-contacts", StoreContactSerializer, filters_example={
    "name": "Иван",
    "role": "Менеджер",
    "phone": "+79990001122",
    "telegram": "@ivan",
    "has_telegram": True,
    "created_at": CREATED_AT_FILTER_EXAMPLE,
})
class StoreContactViewSet(StoreScopedModelViewSet):
    queryset = StoreContact.objects.all()
    serializer_class = StoreContactSerializer


@tagged("store-admin-services", StoreServiceSerializer, filters_example={
    "title": "Пошив",
    "icon": 1,
    "kicker": "Быстро",
    "visible": True,
    "created_at": CREATED_AT_FILTER_EXAMPLE,
})
class StoreServiceViewSet(StoreScopedModelViewSet):
    queryset = StoreService.objects.all()
    serializer_class = StoreServiceSerializer


@tagged("store-admin-colors", StoreColorSerializer, filters_example={
    "name": "Красный",
    "hex_code": "#FF0000",
    "created_at": CREATED_AT_FILTER_EXAMPLE,
})
class StoreColorViewSet(StoreScopedModelViewSet):
    queryset = StoreColor.objects.all()
    serializer_class = StoreColorSerializer


@tagged("store-admin-icons", IconSerializer, filters_example={"name": "shirt"})
class IconViewSet(NoPutModelViewSet):
    """
    Global catalog (not store-scoped - no `store` field on Icon). Any
    authenticated store admin can browse and manage it, since there is no
    separate platform-admin principal in this project yet.
    """

    authentication_classes = [StoreAdminJWTAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = Icon.objects.all()
    serializer_class = IconSerializer

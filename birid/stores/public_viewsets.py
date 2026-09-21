from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework.permissions import AllowAny

from core.viewsets import CREATED_AT_FILTER_EXAMPLE, PublicReadOnlyViewSet, public_tagged

from .models import Store
from .serializers import PublicStoreDetailSerializer, PublicStoreSerializer


@extend_schema_view(retrieve=extend_schema(responses=PublicStoreDetailSerializer))
@public_tagged("public-stores", PublicStoreSerializer, filters_example={
    "name": "Birid virid",
    "created_at": CREATED_AT_FILTER_EXAMPLE,
})
class PublicStoreViewSet(PublicReadOnlyViewSet):
    """Unauthenticated marketplace browsing - only active stores are visible."""

    authentication_classes = []
    permission_classes = [AllowAny]
    serializer_class = PublicStoreSerializer

    def get_queryset(self):
        return Store.objects.filter(active=True).order_by("-created_at")

    def get_serializer_class(self):
        if self.action == "retrieve":
            return PublicStoreDetailSerializer
        return super().get_serializer_class()

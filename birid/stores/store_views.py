from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .authentication import StoreAdminJWTAuthentication
from .serializers import StoreSerializer, StoreUpdateSerializer


class StoreView(APIView):
    """Current store admin's own store - read and edit its 4 editable fields."""

    authentication_classes = [StoreAdminJWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=StoreSerializer, summary="Current store", tags=["stores-store"])
    def get(self, request):
        return Response(StoreSerializer(request.user.store).data)

    @extend_schema(
        request=StoreUpdateSerializer,
        responses=StoreSerializer,
        summary="Update current store",
        tags=["stores-store"],
    )
    def patch(self, request):
        store = request.user.store
        serializer = StoreUpdateSerializer(store, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(StoreSerializer(store).data)

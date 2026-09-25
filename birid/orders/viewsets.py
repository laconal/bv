from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.viewsets import CREATED_AT_FILTER_EXAMPLE, GetAllListMixin, tagged
from stores.authentication import StoreAdminJWTAuthentication

from .models import CancelledBy, OrderStatus, StoreOrder
from .serializers import StoreOrderSerializer, StoreOrderStatusUpdateSerializer

_TAG = "stores-orders"


@extend_schema_view(
    # partial_update really only accepts/validates `status` (see
    # StoreOrderStatusUpdateSerializer) - without this override
    # drf-spectacular defaults to the view's serializer_class
    # (StoreOrderSerializer), which would document the PATCH body as the
    # full order (including read-only fields) instead of its real {status} shape.
    partial_update=extend_schema(
        request=StoreOrderStatusUpdateSerializer, responses=StoreOrderSerializer, tags=[_TAG],
    ),
)
@tagged(_TAG, StoreOrderSerializer, filters_example={
    "status": "pending_confirmation",
    "created_at": CREATED_AT_FILTER_EXAMPLE,
}, actions=("retrieve",))
class StoreOrderViewSet(GetAllListMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """
    Store-admin side: browse own store's orders and move `status` forward
    (PATCH; see ALLOWED_STATUS_TRANSITIONS in orders/models.py). No create -
    orders come from a buyer's checkout (see orders/customer_viewsets.py) -
    and no delete, a placed order is never removed, only cancelled.
    """

    http_method_names = ["get", "post", "patch", "head", "options"]
    authentication_classes = [StoreAdminJWTAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = StoreOrder.objects.all()
    serializer_class = StoreOrderSerializer

    def get_queryset(self):
        return StoreOrder.objects.filter(store=self.request.user.store).prefetch_related("items")

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = StoreOrderStatusUpdateSerializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        extra = {"cancelled_by": CancelledBy.STORE} if serializer.validated_data.get("status") == OrderStatus.CANCELLED else {}
        serializer.save(**extra)
        return Response(StoreOrderSerializer(instance).data)

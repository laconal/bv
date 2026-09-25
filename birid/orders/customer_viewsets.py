from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import mixins, status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from buyers.authentication import BuyerJWTAuthentication
from core.viewsets import CREATED_AT_FILTER_EXAMPLE, GetAllListMixin, tagged

from .models import CancelledBy, OrderStatus, StoreOrder
from .serializers import CustomerOrderCancelSerializer, CustomerOrderCreateSerializer, StoreOrderSerializer

_TAG = "customers-orders"


@extend_schema_view(
    create=extend_schema(request=CustomerOrderCreateSerializer, responses=StoreOrderSerializer, tags=[_TAG]),
    # See StoreOrderViewSet.partial_update's override for why this is
    # needed - without it drf-spectacular would document the PATCH body as
    # the full order instead of its real {status, cancellation_reason} shape.
    partial_update=extend_schema(
        request=CustomerOrderCancelSerializer, responses=StoreOrderSerializer, tags=[_TAG],
        summary="Cancel order (buyer, pending_confirmation only)",
    ),
)
@tagged(_TAG, StoreOrderSerializer, filters_example={
    "status": "pending_confirmation",
    "created_at": CREATED_AT_FILTER_EXAMPLE,
}, actions=("retrieve",))
class CustomerOrderViewSet(GetAllListMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """
    Buyer side: checkout (create), browse own order history, and cancel an
    order while it's still pending_confirmation. Any other status change is
    store-admin only (see orders/viewsets.py).
    """

    http_method_names = ["get", "post", "patch", "head", "options"]
    authentication_classes = [BuyerJWTAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = StoreOrder.objects.all()
    serializer_class = StoreOrderSerializer

    def get_queryset(self):
        return StoreOrder.objects.filter(buyer=self.request.user).prefetch_related("items")

    def create(self, request, *args, **kwargs):
        serializer = CustomerOrderCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        return Response(StoreOrderSerializer(order).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = CustomerOrderCancelSerializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(status=OrderStatus.CANCELLED, cancelled_by=CancelledBy.BUYER)
        return Response(StoreOrderSerializer(instance).data)

from rest_framework import serializers

from products.models import StoreProduct
from products.serializers import PublicProductSerializer
from stores.models import Store

from .models import (
    ALLOWED_STATUS_TRANSITIONS,
    BUYER_CANCELLATION_REASONS,
    OrderStatus,
    PriceType,
    StoreOrder,
    StoreOrderItem,
)
from .services import resolve_price


class StoreOrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoreOrderItem
        fields = [
            "id", "product", "product_snapshot", "quantity", "price_type",
            "base_price", "final_price", "applied_discount",
            "created_at", "updated_at",
        ]


class StoreOrderSerializer(serializers.ModelSerializer):
    """Read shape - identical for both the store-admin side and the buyer side, just two different querysets over it."""

    items = StoreOrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = StoreOrder
        fields = [
            "id", "store", "buyer", "status", "cancelled_by", "cancellation_reason",
            "items", "created_at", "updated_at",
        ]


class StoreOrderStatusUpdateSerializer(serializers.ModelSerializer):
    """
    PATCH .../stores/orders/{id}/ - only `status` (+ `cancellation_reason`
    when cancelling) is writable, and only along ALLOWED_STATUS_TRANSITIONS.
    `cancelled_by` isn't a field here - the view sets it to "store" via
    serializer.save(cancelled_by=...) since it's implied by which endpoint
    this is, not something the caller should be able to pick.
    """

    class Meta:
        model = StoreOrder
        fields = ["status", "cancellation_reason"]

    def validate_status(self, value):
        current = self.instance.status
        allowed_next = ALLOWED_STATUS_TRANSITIONS.get(current, set())
        if value not in allowed_next:
            raise serializers.ValidationError(
                f"Cannot transition from '{current}' to '{value}'. Allowed: {sorted(allowed_next) or 'none (terminal)'}.",
            )
        return value

    def validate(self, attrs):
        if attrs.get("status") == OrderStatus.CANCELLED and not attrs.get("cancellation_reason"):
            raise serializers.ValidationError({"cancellation_reason": "Required when cancelling an order."})
        return attrs


class CustomerOrderCancelSerializer(serializers.ModelSerializer):
    """
    PATCH .../customers/orders/{id}/ - a buyer may only cancel their own
    order, and only while it's still pending_confirmation (once the store
    has confirmed it, only the store can cancel - see
    StoreOrderStatusUpdateSerializer). No `status` field - cancelling is the
    only thing this endpoint does, so it's implied rather than passed in;
    the view sets status=cancelled and cancelled_by="buyer" via
    serializer.save(...).
    """

    class Meta:
        model = StoreOrder
        fields = ["cancellation_reason"]

    def validate_cancellation_reason(self, value):
        if value not in BUYER_CANCELLATION_REASONS:
            raise serializers.ValidationError(
                f"Not a valid buyer cancellation reason. Choose one of: {sorted(r.value for r in BUYER_CANCELLATION_REASONS)}.",
            )
        return value

    def validate(self, attrs):
        if self.instance.status != OrderStatus.PENDING_CONFIRMATION:
            raise serializers.ValidationError(
                {"status": f"Order can only be cancelled while pending confirmation (current: '{self.instance.status}')."},
            )
        if not attrs.get("cancellation_reason"):
            raise serializers.ValidationError({"cancellation_reason": "Required when cancelling an order."})
        return attrs


class OrderItemCreateSerializer(serializers.Serializer):
    product = serializers.PrimaryKeyRelatedField(queryset=StoreProduct.objects.all())
    quantity = serializers.IntegerField(min_value=1)
    price_type = serializers.ChoiceField(choices=PriceType.choices)


class CustomerOrderCreateSerializer(serializers.Serializer):
    """
    Checkout: the frontend's cart (never stored server-side) is split by
    store before calling this - each call creates exactly one StoreOrder,
    for exactly one store, from a list of {product, quantity, price_type}.
    """

    store = serializers.PrimaryKeyRelatedField(queryset=Store.objects.filter(active=True))
    items = OrderItemCreateSerializer(many=True)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("At least one item is required.")
        return value

    def validate(self, attrs):
        store = attrs["store"]
        for item in attrs["items"]:
            product = item["product"]
            if product.store_id != store.id:
                raise serializers.ValidationError(
                    {"items": f"Product {product.id} does not belong to the selected store."},
                )
            price_type = item["price_type"]
            if price_type == PriceType.SALE and not (product.is_sellable and product.price_sale is not None):
                raise serializers.ValidationError({"items": f"Product {product.id} is not available for sale."})
            if price_type == PriceType.RENTAL and not (product.is_rentable and product.price_rental is not None):
                raise serializers.ValidationError({"items": f"Product {product.id} is not available for rental."})
            if price_type == PriceType.TAILORING and product.price_tailoring is None:
                raise serializers.ValidationError({"items": f"Product {product.id} is not available for tailoring."})
        return attrs

    def create(self, validated_data):
        buyer = self.context["request"].user
        store = validated_data["store"]

        order = StoreOrder.objects.create(store=store, buyer=buyer)
        for item in validated_data["items"]:
            product = item["product"]
            price_type = item["price_type"]
            base_price, final_price, applied_discount = resolve_price(product, price_type)
            StoreOrderItem.objects.create(
                store=store, order=order, product=product,
                product_snapshot=PublicProductSerializer(product).data,
                quantity=item["quantity"], price_type=price_type,
                base_price=base_price, final_price=final_price, applied_discount=applied_discount,
            )
        return order

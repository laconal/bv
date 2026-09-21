from django.core.serializers.json import DjangoJSONEncoder
from django.db import models

from core.models import TimestampedModel
from products.models import StoreProduct
from stores.models import Store


class OrderStatus(models.TextChoices):
    PENDING_CONFIRMATION = "pending_confirmation", "Pending confirmation"
    CONFIRMED = "confirmed", "Confirmed"
    DELIVERED = "delivered", "Delivered"
    CLOSED = "closed", "Closed"
    CANCELLED = "cancelled", "Cancelled"
    RETURNED = "returned", "Returned"


# Only these next-status sets are reachable from a given status (enforced in
# orders/serializers.py's StoreOrderStatusUpdateSerializer, not just at the
# DB level - see the discussion that led to this: delivery is a one-way
# door, cancellation is only possible before it, closed/cancelled/returned
# are terminal).
ALLOWED_STATUS_TRANSITIONS = {
    OrderStatus.PENDING_CONFIRMATION: {OrderStatus.CONFIRMED, OrderStatus.CANCELLED},
    OrderStatus.CONFIRMED: {OrderStatus.DELIVERED, OrderStatus.CANCELLED},
    OrderStatus.DELIVERED: {OrderStatus.CLOSED, OrderStatus.RETURNED},
    OrderStatus.CLOSED: set(),
    OrderStatus.CANCELLED: set(),
    OrderStatus.RETURNED: set(),
}


class PriceType(models.TextChoices):
    SALE = "sale", "Sale"
    RENTAL = "rental", "Rental"
    TAILORING = "tailoring", "Tailoring"


class CancelledBy(models.TextChoices):
    BUYER = "buyer", "Buyer"
    STORE = "store", "Store"


class CancellationReason(models.TextChoices):
    # Buyer-side reasons (also the only ones a buyer is allowed to pick from
    # - see orders/serializers.py's CustomerOrderCancelSerializer).
    CHANGED_MIND = "changed_mind", "Buyer changed their mind"
    FOUND_BETTER_PRICE = "found_better_price", "Found a better price elsewhere"
    ORDERED_BY_MISTAKE = "ordered_by_mistake", "Ordered by mistake"
    DELIVERY_TOO_SLOW = "delivery_too_slow", "Delivery is taking too long"
    # Store-side reasons - a store admin can use any reason in this enum,
    # including the buyer-side ones above (e.g. the buyer called and asked).
    OUT_OF_STOCK = "out_of_stock", "Product out of stock"
    CANNOT_FULFILL = "cannot_fulfill", "Store cannot fulfill the order"
    BUYER_UNREACHABLE = "buyer_unreachable", "Could not reach the buyer"
    SUSPECTED_FRAUD = "suspected_fraud", "Suspected fraudulent order"
    OTHER = "other", "Other"


BUYER_CANCELLATION_REASONS = {
    CancellationReason.CHANGED_MIND,
    CancellationReason.FOUND_BETTER_PRICE,
    CancellationReason.ORDERED_BY_MISTAKE,
    CancellationReason.DELIVERY_TOO_SLOW,
    CancellationReason.OTHER,
}


class StoreOrder(TimestampedModel):
    """
    Always belongs to exactly one store - a cart spanning multiple stores
    becomes one StoreOrder per store on checkout (see
    orders/serializers.py's CustomerOrderCreateSerializer).
    """

    ALLOWED_FILTERS = {"status", "buyer", "created_at"}

    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="orders")
    buyer = models.ForeignKey("buyers.Buyer", on_delete=models.CASCADE, related_name="orders")
    status = models.CharField(max_length=30, choices=OrderStatus.choices, default=OrderStatus.PENDING_CONFIRMATION)

    # Only set once status becomes "cancelled" - who cancelled it and why.
    cancelled_by = models.CharField(max_length=10, choices=CancelledBy.choices, null=True, blank=True)
    cancellation_reason = models.CharField(
        max_length=30, choices=CancellationReason.choices, null=True, blank=True,
    )

    def __str__(self) -> str:
        return f"Order #{self.id} ({self.store_id})"


class StoreOrderItem(TimestampedModel):
    """
    One product line within a StoreOrder. `product` is kept for
    joins/analytics but is nullable - it must survive the underlying
    product being deleted later, which is exactly what `product_snapshot`
    is for (a full, immutable copy of the product as it was at order time).
    """

    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="order_items")
    order = models.ForeignKey(StoreOrder, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(
        StoreProduct, on_delete=models.SET_NULL, null=True, blank=True, related_name="order_items",
    )
    product_snapshot = models.JSONField(encoder=DjangoJSONEncoder)

    quantity = models.PositiveIntegerField()
    price_type = models.CharField(max_length=20, choices=PriceType.choices)

    # Per-unit, not per-line - multiply by quantity for the line total.
    base_price = models.DecimalField(max_digits=30, decimal_places=2)
    final_price = models.DecimalField(max_digits=30, decimal_places=2)

    # Snapshot of whichever single discount (the one giving the largest
    # reduction - see orders/services.py) was applied, or null if none was.
    applied_discount = models.JSONField(null=True, blank=True, encoder=DjangoJSONEncoder)

    def __str__(self) -> str:
        return f"Item #{self.id} of order {self.order_id}"

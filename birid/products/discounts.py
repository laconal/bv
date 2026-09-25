from django.db.models import Prefetch, Q
from django.utils import timezone

from .models import DiscountStatus, StoreDiscountProduct

# to_attr the prefetch below stores each product's active discounts under.
_PREFETCHED_ATTR = "prefetched_active_discounts"


def _active_discount_products_queryset():
    """
    StoreDiscountProduct rows whose parent StoreDiscount is currently active:
    status=active and the current moment falls inside its [starts_at,
    ends_at] window (either bound may be unset).
    """
    now = timezone.now()
    return StoreDiscountProduct.objects.filter(
        discount__status=DiscountStatus.ACTIVE,
    ).filter(
        Q(discount__starts_at__isnull=True) | Q(discount__starts_at__lte=now),
    ).filter(
        Q(discount__ends_at__isnull=True) | Q(discount__ends_at__gte=now),
    ).select_related("discount")


def prefetch_active_discounts() -> Prefetch:
    """
    For a product list queryset - loads every listed product's active
    discounts in one query, which active_discount_products() then reads
    instead of querying per product. Build it per request: "active" is
    evaluated against the current time when this is called.
    """
    return Prefetch("product_discounts", queryset=_active_discount_products_queryset(), to_attr=_PREFETCHED_ATTR)


def active_discount_products(product):
    """
    Currently-active StoreDiscountProduct rows for `product` - from
    prefetch_active_discounts() when the product was loaded with it,
    otherwise queried directly. Shared by PublicProductSerializer.get_discounts
    (products/serializers.py) and the order checkout price resolver
    (orders/services.py).
    """
    prefetched = getattr(product, _PREFETCHED_ATTR, None)
    if prefetched is not None:
        return prefetched
    return _active_discount_products_queryset().filter(product=product)

from django.db.models import Q
from django.utils import timezone

from .models import DiscountStatus


def active_discount_products(product):
    """
    Currently-active StoreDiscountProduct rows for `product` - "active"
    means the parent StoreDiscount is status=active and the current moment
    falls inside its [starts_at, ends_at] window (either bound may be unset).
    Shared by PublicProductSerializer.get_discounts (products/serializers.py)
    and the order checkout price resolver (orders/services.py).
    """
    now = timezone.now()
    return product.product_discounts.filter(
        discount__status=DiscountStatus.ACTIVE,
    ).filter(
        Q(discount__starts_at__isnull=True) | Q(discount__starts_at__lte=now),
    ).filter(
        Q(discount__ends_at__isnull=True) | Q(discount__ends_at__gte=now),
    ).select_related("discount")

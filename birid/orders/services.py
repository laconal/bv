from decimal import Decimal

from products.discounts import active_discount_products
from products.models import DiscountType, StoreProduct

from .models import PriceType

_PRICE_FIELD = {
    PriceType.SALE: "price_sale",
    PriceType.RENTAL: "price_rental",
    PriceType.TAILORING: "price_tailoring",
}


def base_price_for(product: StoreProduct, price_type: str) -> Decimal:
    return getattr(product, _PRICE_FIELD[price_type])


def resolve_price(product: StoreProduct, price_type: str) -> tuple[Decimal, Decimal, dict | None]:
    """
    Returns (base_price, final_price, applied_discount) for one unit of
    `product` bought as `price_type`, right now. If more than one discount
    is currently active on the product, the one giving the largest
    reduction wins - applied_discount is a snapshot of just that one (or
    None if no active discount beats a 0 reduction).
    """
    base_price = base_price_for(product, price_type)

    best_reduction = Decimal("0")
    best = None
    for discount_product in active_discount_products(product):
        if discount_product.discount_type == DiscountType.PERCENTAGE:
            reduction = (base_price * discount_product.value / Decimal("100")).quantize(Decimal("0.01"))
        else:
            reduction = discount_product.value
        reduction = min(reduction, base_price)
        if reduction > best_reduction:
            best_reduction = reduction
            best = discount_product

    if best is None:
        return base_price, base_price, None

    final_price = base_price - best_reduction
    applied_discount = {
        "discount_id": best.discount_id,
        "title": best.discount.title,
        "discount_type": best.discount_type,
        "value": str(best.value),
        "reduction": str(best_reduction),
    }
    return base_price, final_price, applied_discount

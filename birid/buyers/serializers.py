from rest_framework import serializers

from products.models import StoreProduct

from .models import Buyer


class FavoriteProductSerializer(serializers.ModelSerializer):
    """Summary shape for a buyer's favorited products - not the full store-admin product serializer."""

    class Meta:
        model = StoreProduct
        fields = [
            "id", "store", "name", "slug", "category",
            "price_sale", "price_rental", "is_sellable", "is_rentable",
        ]


class BuyerMeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Buyer
        fields = [
            "id", "login", "active",
            "last_name", "first_name", "middle_name", "age", "gender", "city",
            "avatar_photo", "avatar_photo_processed", "avatar_processing_status",
            "created_at", "updated_at",
        ]


class BuyerUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Buyer
        fields = ["last_name", "first_name", "middle_name", "age", "gender", "city", "avatar_photo"]

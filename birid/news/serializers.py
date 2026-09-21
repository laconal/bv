from rest_framework import serializers

from .models import StoreNews


class StoreNewsSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoreNews
        fields = [
            "id", "title", "news_type", "slug", "description",
            "starts_at", "ends_at", "status", "products",
            "created_at", "updated_at",
        ]

    def validate_products(self, value):
        request = self.context["request"]
        for product in value:
            if product.store_id != request.user.store_id:
                raise serializers.ValidationError("One or more products do not belong to your store.")
        return value

    def validate(self, attrs):
        starts_at = attrs.get("starts_at", getattr(self.instance, "starts_at", None))
        ends_at = attrs.get("ends_at", getattr(self.instance, "ends_at", None))
        if starts_at is not None and ends_at is not None and ends_at < starts_at:
            raise serializers.ValidationError({"ends_at": "Must not be earlier than starts_at."})
        return attrs


class PublicStoreNewsSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoreNews
        fields = [
            "id", "store", "title", "news_type", "slug", "description",
            "starts_at", "ends_at", "status", "products",
            "created_at", "updated_at",
        ]

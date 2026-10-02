from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from products.models import StoreProductPhoto
from products.serializers import StoreProductPhotoSerializer
from products.tasks import generate_photo_renditions

from .models import StoreNews


class StoreNewsSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = StoreNews
        fields = [
            "id", "title", "news_type", "slug", "description",
            "starts_at", "ends_at", "status", "products", "image",
            "created_at", "updated_at",
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["image"] = StoreProductPhotoSerializer(instance.image).data if instance.image_id else None
        return data

    def create(self, validated_data):
        image_file = validated_data.pop("image", None)
        news = super().create(validated_data)
        if image_file is not None:
            self._attach_image(news, image_file)
        return news

    def update(self, instance, validated_data):
        has_image = "image" in validated_data
        image_file = validated_data.pop("image", None)
        news = super().update(instance, validated_data)
        if has_image:
            self._attach_image(news, image_file)
        return news

    def _attach_image(self, news, image_file):
        """Uploads straight into a new StoreProductPhoto and kicks off its renditions - see StoreProductPhotoViewSet.perform_create."""
        if image_file is None:
            news.image = None
            news.save(update_fields=["image", "updated_at"])
            return
        photo = StoreProductPhoto.objects.create(store=news.store, image=image_file)
        generate_photo_renditions.delay(photo.id)
        news.image = photo
        news.save(update_fields=["image", "updated_at"])

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


class StoreNewsResponseSerializer(StoreNewsSerializer):
    """
    Doc-only (never actually instantiated to serialize a response - see
    news/viewsets.py) - mirrors products' StoreProductResponseSerializer:
    `image` is write_only (a plain photo id on input) with its real
    nested-with-renditions shape injected by to_representation(), which
    drf-spectacular can't see statically.
    """

    image = StoreProductPhotoSerializer(read_only=True)


class PublicStoreNewsSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = StoreNews
        fields = [
            "id", "store", "title", "news_type", "slug", "description",
            "starts_at", "ends_at", "status", "products", "image",
            "created_at", "updated_at",
        ]

    @extend_schema_field(StoreProductPhotoSerializer)
    def get_image(self, obj):
        if not obj.image_id:
            return None
        return StoreProductPhotoSerializer(obj.image).data

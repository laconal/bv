from decimal import Decimal

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .discounts import active_discount_products
from .models import (
    DiscountType,
    StoreCategory,
    StoreDiscount,
    StoreDiscountProduct,
    StoreProduct,
    StoreProductPhoto,
    StoreProductPhotoRendition,
    StoreProductVariant,
    StoreTag,
)


class StoreCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = StoreCategory
        fields = [
            "id", "name", "parent",
            "cover", "cover_processed", "cover_processing_status",
            "created_at", "updated_at",
        ]
        read_only_fields = ["cover_processed", "cover_processing_status"]

    def validate_parent(self, value):
        if value is None:
            return value
        request = self.context["request"]
        if value.store_id != request.user.store_id:
            raise serializers.ValidationError("Parent category does not belong to your store.")
        if self.instance is not None and value.id == self.instance.id:
            raise serializers.ValidationError("A category cannot be its own parent.")
        return value


class StoreTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoreTag
        fields = ["id", "name", "created_at", "updated_at"]


class PhotoRenditionSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoreProductPhotoRendition
        fields = ["id", "quality", "image", "created_at"]


class StoreProductPhotoSerializer(serializers.ModelSerializer):
    renditions = PhotoRenditionSerializer(many=True, read_only=True)

    class Meta:
        model = StoreProductPhoto
        fields = [
            "id", "image", "original_filename", "processing_status", "renditions",
            "created_at", "updated_at",
        ]
        read_only_fields = ["original_filename", "processing_status"]


class StoreProductVariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoreProductVariant
        fields = ["id", "product", "photos", "created_at", "updated_at"]

    def validate_product(self, value):
        request = self.context["request"]
        if value.store_id != request.user.store_id:
            raise serializers.ValidationError("Product does not belong to your store.")
        return value

    def validate_photos(self, value):
        request = self.context["request"]
        for photo in value:
            if photo.store_id != request.user.store_id:
                raise serializers.ValidationError("One or more photos do not belong to your store.")
        return value


class ProductVariantWriteSerializer(serializers.ModelSerializer):
    """Nested under StoreProductSerializer - no `product` field, it's implied by the parent."""

    photos = serializers.PrimaryKeyRelatedField(queryset=StoreProductPhoto.objects.all(), many=True, required=False)

    class Meta:
        model = StoreProductVariant
        fields = ["photos"]


class ProductVariantReadSerializer(serializers.ModelSerializer):
    photos = StoreProductPhotoSerializer(many=True, read_only=True)

    class Meta:
        model = StoreProductVariant
        fields = ["id", "photos", "created_at", "updated_at"]


class StoreProductSerializer(serializers.ModelSerializer):
    variants = ProductVariantWriteSerializer(many=True, required=False, write_only=True)
    in_customers_saved = serializers.SerializerMethodField()

    class Meta:
        model = StoreProduct
        fields = [
            "id", "name", "category", "subcategory", "description", "brand", "manufacture", "material", "slug",
            "tags", "color", "size",
            "price_sale", "price_rental", "price_tailoring",
            "is_sellable", "is_rentable", "blur_image_in_site",
            "views", "in_customers_saved",
            "variants",
            "created_at", "updated_at",
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["variants"] = ProductVariantReadSerializer(
            instance.variants.all(), many=True, context=self.context,
        ).data
        return data

    @extend_schema_field(serializers.IntegerField())
    def get_in_customers_saved(self, obj):
        return obj.favorited_by_buyers.count()

    def validate_variants(self, value):
        request = self.context["request"]
        for variant_data in value:
            for photo in variant_data.get("photos", []):
                if photo.store_id != request.user.store_id:
                    raise serializers.ValidationError("One or more photos do not belong to your store.")
        return value

    def create(self, validated_data):
        variants_data = validated_data.pop("variants", [])
        product = super().create(validated_data)
        for variant_data in variants_data:
            variant = StoreProductVariant.objects.create(store=product.store, product=product)
            photos = variant_data.get("photos")
            if photos:
                variant.photos.set(photos)
        return product

    def update(self, instance, validated_data):
        # Nested variant writes are create-time only for now - PATCH leaves existing variants untouched.
        validated_data.pop("variants", None)
        return super().update(instance, validated_data)

    def validate_category(self, value):
        request = self.context["request"]
        if value.store_id != request.user.store_id:
            raise serializers.ValidationError("Category does not belong to your store.")
        return value

    def validate_subcategory(self, value):
        if value is None:
            return value
        request = self.context["request"]
        if value.store_id != request.user.store_id:
            raise serializers.ValidationError("Subcategory does not belong to your store.")
        return value

    def validate_color(self, value):
        if value is None:
            return value
        request = self.context["request"]
        if value.store_id != request.user.store_id:
            raise serializers.ValidationError("Color does not belong to your store.")
        return value

    def validate_tags(self, value):
        request = self.context["request"]
        for tag in value:
            if tag.store_id != request.user.store_id:
                raise serializers.ValidationError("One or more tags do not belong to your store.")
        return value

    def validate(self, attrs):
        category = attrs.get("category", getattr(self.instance, "category", None))
        subcategory = attrs.get("subcategory", getattr(self.instance, "subcategory", None))
        if subcategory is not None and category is not None and subcategory.parent_id != category.id:
            raise serializers.ValidationError(
                {"subcategory": "Subcategory must be a child of the selected category."}
            )
        return attrs


class StoreProductResponseSerializer(StoreProductSerializer):
    """
    Doc-only (never actually instantiated to serialize a response - see
    products/viewsets.py). StoreProductSerializer.variants is write_only (a
    plain photo-id list on input) with the real nested-read shape injected by
    its to_representation() override; drf-spectacular can't see that
    override statically, so without this it omits `variants` from the
    response schema entirely. This subclass just redeclares that one field
    with its actual read shape so the generated schema matches reality.
    """

    variants = ProductVariantReadSerializer(many=True, read_only=True)


class PublicProductDiscountSerializer(serializers.ModelSerializer):
    """
    A currently-active discount applied to one product, from the buyer's
    point of view - discount_type/value are per-product (see
    StoreDiscountProduct), the rest comes from the parent StoreDiscount.
    """

    title = serializers.CharField(source="discount.title")
    description = serializers.CharField(source="discount.description")
    starts_at = serializers.DateTimeField(source="discount.starts_at")
    ends_at = serializers.DateTimeField(source="discount.ends_at")

    class Meta:
        model = StoreDiscountProduct
        fields = ["id", "discount", "title", "description", "discount_type", "value", "starts_at", "ends_at"]


class PublicProductSerializer(serializers.ModelSerializer):
    """Unauthenticated storefront view of a product - read-only, so `variants` can just be its real read shape directly."""

    variants = ProductVariantReadSerializer(many=True, read_only=True)
    discounts = serializers.SerializerMethodField()
    in_customers_saved = serializers.SerializerMethodField()

    class Meta:
        model = StoreProduct
        fields = [
            "id", "store", "name", "category", "subcategory", "description", "brand", "manufacture", "material",
            "slug", "tags", "color", "size",
            "price_sale", "price_rental", "price_tailoring",
            "is_sellable", "is_rentable", "blur_image_in_site",
            "views", "in_customers_saved",
            "variants", "discounts",
            "created_at", "updated_at",
        ]

    @extend_schema_field(serializers.IntegerField())
    def get_in_customers_saved(self, obj):
        return obj.favorited_by_buyers.count()

    @extend_schema_field(PublicProductDiscountSerializer(many=True))
    def get_discounts(self, obj):
        return PublicProductDiscountSerializer(active_discount_products(obj), many=True).data


class DiscountProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoreDiscountProduct
        fields = ["id", "product", "discount_type", "value", "created_at", "updated_at"]

    def validate_product(self, value):
        request = self.context["request"]
        if value.store_id != request.user.store_id:
            raise serializers.ValidationError("Product does not belong to your store.")
        return value

    def validate(self, attrs):
        discount_type = attrs.get("discount_type", getattr(self.instance, "discount_type", None))
        value = attrs.get("value", getattr(self.instance, "value", None))
        if value is not None:
            if value <= 0:
                raise serializers.ValidationError({"value": "Must be positive."})
            if discount_type == DiscountType.PERCENTAGE and value > Decimal("100"):
                raise serializers.ValidationError({"value": "A percentage discount can't exceed 100."})
        return attrs


class StoreDiscountSerializer(serializers.ModelSerializer):
    products = DiscountProductSerializer(source="discount_products", many=True, required=False)

    class Meta:
        model = StoreDiscount
        fields = [
            "id", "title", "description", "starts_at", "ends_at", "status", "products",
            "created_at", "updated_at",
        ]

    def validate(self, attrs):
        starts_at = attrs.get("starts_at", getattr(self.instance, "starts_at", None))
        ends_at = attrs.get("ends_at", getattr(self.instance, "ends_at", None))
        if starts_at is not None and ends_at is not None and ends_at < starts_at:
            raise serializers.ValidationError({"ends_at": "Must not be earlier than starts_at."})
        return attrs

    def create(self, validated_data):
        products_data = validated_data.pop("discount_products", [])
        discount = super().create(validated_data)
        self._sync_products(discount, products_data)
        return discount

    def update(self, instance, validated_data):
        products_data = validated_data.pop("discount_products", None)
        discount = super().update(instance, validated_data)
        if products_data is not None:
            discount.discount_products.all().delete()
            self._sync_products(discount, products_data)
        return discount

    def _sync_products(self, discount, products_data):
        for item in products_data:
            StoreDiscountProduct.objects.create(
                store_id=discount.store_id,
                discount=discount,
                product=item["product"],
                discount_type=item["discount_type"],
                value=item["value"],
            )

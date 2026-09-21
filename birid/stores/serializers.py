from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import (
    Icon,
    Store,
    StoreAddress,
    StoreAdmin,
    StoreColor,
    StoreContact,
    StoreService,
    StoreSocialLink,
)


class StoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Store
        fields = ["id", "name", "description", "phone", "email", "active", "created_at", "updated_at"]


class StoreUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Store
        fields = ["name", "description", "phone", "email"]


class StoreAdminMeSerializer(serializers.ModelSerializer):
    store = StoreSerializer(read_only=True)

    class Meta:
        model = StoreAdmin
        fields = ["id", "login", "active", "store", "created_at", "updated_at"]


class IconSerializer(serializers.ModelSerializer):
    class Meta:
        model = Icon
        fields = ["id", "name"]


class StoreSocialLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoreSocialLink
        fields = ["id", "platform", "nickname", "url", "visible", "created_at", "updated_at"]


class StoreAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoreAddress
        fields = ["id", "name", "address", "landmark", "working_hours", "phone", "created_at", "updated_at"]


class StoreContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoreContact
        fields = ["id", "name", "role", "phone", "hours", "telegram", "has_telegram", "created_at", "updated_at"]


class StoreServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoreService
        fields = ["id", "icon", "title", "kicker", "description", "visible", "created_at", "updated_at"]


class StoreColorSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoreColor
        fields = ["id", "name", "hex_code", "created_at", "updated_at"]


class PublicStoreSerializer(serializers.ModelSerializer):
    """
    Unauthenticated storefront view of a Store. social_links/services are
    filtered to visible=True - that flag exists specifically to let a store
    admin hide an entry from the public page while keeping it around in
    their own admin panel. addresses/contacts have no such flag, so all of
    them are shown as-is.
    """

    social_links = serializers.SerializerMethodField()
    services = serializers.SerializerMethodField()
    addresses = StoreAddressSerializer(many=True, read_only=True)
    contacts = StoreContactSerializer(many=True, read_only=True)

    class Meta:
        model = Store
        fields = [
            "id", "name", "description", "phone", "email",
            "social_links", "addresses", "contacts", "services",
            "created_at", "updated_at",
        ]

    @extend_schema_field(StoreSocialLinkSerializer(many=True))
    def get_social_links(self, obj):
        return StoreSocialLinkSerializer(obj.social_links.filter(visible=True), many=True).data

    @extend_schema_field(StoreServiceSerializer(many=True))
    def get_services(self, obj):
        return StoreServiceSerializer(obj.services.filter(visible=True), many=True).data


class PublicStoreDetailSerializer(PublicStoreSerializer):
    """
    Single-store public view - adds aggregate counts that only make sense
    (and are only worth the extra queries) for one store at a time, not the
    whole get-all list. `categories`/`subcategories` are both StoreCategory
    rows (products.models) - a subcategory is just one with `parent` set.
    """

    total_products = serializers.SerializerMethodField()
    total_categories = serializers.SerializerMethodField()
    total_subcategories = serializers.SerializerMethodField()

    class Meta(PublicStoreSerializer.Meta):
        fields = PublicStoreSerializer.Meta.fields + ["total_products", "total_categories", "total_subcategories"]

    @extend_schema_field(serializers.IntegerField())
    def get_total_products(self, obj):
        return obj.products.count()

    @extend_schema_field(serializers.IntegerField())
    def get_total_categories(self, obj):
        return obj.categories.filter(parent__isnull=True).count()

    @extend_schema_field(serializers.IntegerField())
    def get_total_subcategories(self, obj):
        return obj.categories.filter(parent__isnull=False).count()

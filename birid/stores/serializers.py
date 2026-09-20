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

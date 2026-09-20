from rest_framework import serializers


class LoginRequestSerializer(serializers.Serializer):
    login = serializers.CharField()
    password = serializers.CharField(write_only=True)


class RefreshRequestSerializer(serializers.Serializer):
    refreshToken = serializers.CharField()


class TokenPairResponseSerializer(serializers.Serializer):
    accessToken = serializers.CharField()
    refreshToken = serializers.CharField()


class PageRequestSerializer(serializers.Serializer):
    """page/pageSize only - for body-driven list endpoints with no filtering support."""

    page = serializers.IntegerField(required=False, min_value=1, default=1)
    pageSize = serializers.IntegerField(required=False, min_value=1, max_value=100, default=20)


class GetAllRequestSerializer(serializers.Serializer):
    page = serializers.IntegerField(required=False, min_value=1, default=1)
    pageSize = serializers.IntegerField(required=False, min_value=1, max_value=100, default=20)
    filters = serializers.JSONField(
        required=False, default=dict,
        help_text="{field: value} for exact/icontains match, {field: [v1, v2]} for IN, "
                   "{field: {\"eq\"|\"gt\"|\"gte\"|\"lt\"|\"lte\": value}} for comparisons. "
                   "created_at/updated_at compare by calendar date only (time-of-day is ignored). "
                   "Allowed fields are per-resource - see each model's ALLOWED_FILTERS.",
    )

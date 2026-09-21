from datetime import timedelta

from django.db.models import Count, Q, Sum
from django.utils import timezone
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.pagination import paginate_body
from core.viewsets import paginated_serializer
from stores.authentication import StoreAdminJWTAuthentication

from .models import StoreCategory, StoreProduct

_TAG = "stores-reports"

# from_date/to_date compare by calendar date only (StoreProductView/
# BuyerFavoriteProduct.created_at are filtered via `__date`) - matches the
# date-only convention used for created_at/updated_at filters elsewhere
# (see core/filtering.py).
_PERIOD_EXAMPLE = {"page": 1, "pageSize": 20, "from_date": "2026-08-22", "to_date": "2026-09-21"}


class ReportPeriodRequestSerializer(serializers.Serializer):
    page = serializers.IntegerField(required=False, min_value=1, default=1)
    pageSize = serializers.IntegerField(required=False, min_value=1, max_value=100, default=20)
    from_date = serializers.DateField(required=False, help_text="Defaults to 30 days before to_date.")
    to_date = serializers.DateField(required=False, help_text="Defaults to today.")


class StoreReportSummarySerializer(serializers.Serializer):
    total_products = serializers.IntegerField()
    total_categories = serializers.IntegerField()
    total_viewed_products = serializers.IntegerField(help_text="Sum of `views` across all of the store's products.")


class ProductViewReportItemSerializer(serializers.ModelSerializer):
    view_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = StoreProduct
        fields = ["id", "name", "slug", "category", "price_sale", "price_rental", "view_count"]


class ProductFavoriteReportItemSerializer(serializers.ModelSerializer):
    favorite_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = StoreProduct
        fields = ["id", "name", "slug", "category", "price_sale", "price_rental", "favorite_count"]


class CategoryReportItemSerializer(serializers.ModelSerializer):
    view_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = StoreCategory
        fields = ["id", "name", "parent", "view_count"]


def _resolve_period(validated_data: dict):
    to_date = validated_data.get("to_date") or timezone.localdate()
    from_date = validated_data.get("from_date") or (to_date - timedelta(days=30))
    return validated_data["page"], validated_data["pageSize"], from_date, to_date


class StoreReportSummaryView(APIView):
    """Current store's totals - products, categories, and how many products have been viewed at least once."""

    authentication_classes = [StoreAdminJWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=StoreReportSummarySerializer, summary="Store totals", tags=[_TAG])
    def get(self, request):
        store = request.user.store
        data = {
            "total_products": StoreProduct.objects.filter(store=store).count(),
            "total_categories": StoreCategory.objects.filter(store=store).count(),
            "total_viewed_products": StoreProduct.objects.filter(store=store).aggregate(total=Sum("views"))["total"] or 0,
        }
        return Response(StoreReportSummarySerializer(data).data)


class MostViewedProductsReportView(APIView):
    """Products ranked by number of authenticated-buyer views within [from_date, to_date] (default: last 30 days)."""

    authentication_classes = [StoreAdminJWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=ReportPeriodRequestSerializer,
        responses=paginated_serializer(ProductViewReportItemSerializer),
        summary="Most viewed products",
        tags=[_TAG],
        examples=[OpenApiExample("Example", value=_PERIOD_EXAMPLE, request_only=True)],
    )
    def post(self, request):
        req = ReportPeriodRequestSerializer(data=request.data)
        req.is_valid(raise_exception=True)
        page, page_size, from_date, to_date = _resolve_period(req.validated_data)

        queryset = StoreProduct.objects.filter(store=request.user.store).annotate(
            view_count=Count(
                "view_events",
                filter=Q(view_events__created_at__date__gte=from_date, view_events__created_at__date__lte=to_date),
            ),
        ).order_by("-view_count", "-id")

        result = paginate_body(queryset, page, page_size)
        serializer = ProductViewReportItemSerializer(result["items"], many=True)
        return Response({
            "items": serializer.data, "page": result["page"],
            "totalPages": result["totalPages"], "total": result["total"],
        })


class MostFavoritedProductsReportView(APIView):
    """Products ranked by number of buyers who favorited them within [from_date, to_date] (default: last 30 days)."""

    authentication_classes = [StoreAdminJWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=ReportPeriodRequestSerializer,
        responses=paginated_serializer(ProductFavoriteReportItemSerializer),
        summary="Most favorited products",
        tags=[_TAG],
        examples=[OpenApiExample("Example", value=_PERIOD_EXAMPLE, request_only=True)],
    )
    def post(self, request):
        req = ReportPeriodRequestSerializer(data=request.data)
        req.is_valid(raise_exception=True)
        page, page_size, from_date, to_date = _resolve_period(req.validated_data)

        queryset = StoreProduct.objects.filter(store=request.user.store).annotate(
            favorite_count=Count(
                "favorite_events",
                filter=Q(
                    favorite_events__created_at__date__gte=from_date,
                    favorite_events__created_at__date__lte=to_date,
                ),
            ),
        ).order_by("-favorite_count", "-id")

        result = paginate_body(queryset, page, page_size)
        serializer = ProductFavoriteReportItemSerializer(result["items"], many=True)
        return Response({
            "items": serializer.data, "page": result["page"],
            "totalPages": result["totalPages"], "total": result["total"],
        })


class MostPopularCategoriesReportView(APIView):
    """
    Categories ranked by total views of their directly-assigned products
    within [from_date, to_date] (default: last 30 days). Only counts a
    product toward its `category`, not a category it's used as `subcategory`
    for - a subcategory accrues its own views the same way.
    """

    authentication_classes = [StoreAdminJWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=ReportPeriodRequestSerializer,
        responses=paginated_serializer(CategoryReportItemSerializer),
        summary="Most popular categories",
        tags=[_TAG],
        examples=[OpenApiExample("Example", value=_PERIOD_EXAMPLE, request_only=True)],
    )
    def post(self, request):
        req = ReportPeriodRequestSerializer(data=request.data)
        req.is_valid(raise_exception=True)
        page, page_size, from_date, to_date = _resolve_period(req.validated_data)

        queryset = StoreCategory.objects.filter(store=request.user.store).annotate(
            view_count=Count(
                "products_in_category__view_events",
                filter=Q(
                    products_in_category__view_events__created_at__date__gte=from_date,
                    products_in_category__view_events__created_at__date__lte=to_date,
                ),
            ),
        ).order_by("-view_count", "-id")

        result = paginate_body(queryset, page, page_size)
        serializer = CategoryReportItemSerializer(result["items"], many=True)
        return Response({
            "items": serializer.data, "page": result["page"],
            "totalPages": result["totalPages"], "total": result["total"],
        })

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import exceptions, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.exceptions import InvalidCredentials
from core.pagination import paginate_body
from core.serializers import (
    LoginRequestSerializer,
    PageRequestSerializer,
    RefreshRequestSerializer,
    TokenPairResponseSerializer,
)
from core.viewsets import paginated_serializer
from products.models import StoreProduct
from stores.models import Store
from stores.serializers import StoreSerializer

from .authentication import BuyerJWTAuthentication
from .models import Buyer, BuyerAvatarProcessingStatus
from .security import buyer_jwt
from .serializers import BuyerMeSerializer, BuyerUpdateSerializer, FavoriteProductSerializer
from .tasks import process_buyer_avatar

_FAVORITE_ADDED_RESPONSE = OpenApiResponse(description="Added to favorites.")
_FAVORITE_REMOVED_RESPONSE = OpenApiResponse(description="Removed from favorites.")


def _issue_token_pair(account: Buyer) -> dict:
    payload = {"id": account.id, "login": account.login}
    return {
        "accessToken": buyer_jwt.create_access_token(payload),
        "refreshToken": buyer_jwt.create_refresh_token(payload),
    }


class BuyerLoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        request=LoginRequestSerializer,
        responses=TokenPairResponseSerializer,
        summary="Buyer login",
        tags=["Buyer auth"],
    )
    def post(self, request):
        serializer = LoginRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        account = Buyer.objects.filter(login=serializer.validated_data["login"]).first()
        if account is None or not account.check_password(serializer.validated_data["password"]):
            raise InvalidCredentials()
        if not account.active:
            raise exceptions.PermissionDenied("Account is inactive")

        return Response(_issue_token_pair(account))


class BuyerMeView(APIView):
    """Current buyer's own profile - read and edit it (name/age/gender/city/avatar)."""

    authentication_classes = [BuyerJWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=BuyerMeSerializer, summary="Current buyer", tags=["Buyer auth"])
    def get(self, request):
        return Response(BuyerMeSerializer(request.user).data)

    @extend_schema(
        request=BuyerUpdateSerializer,
        responses=BuyerMeSerializer,
        summary="Update current buyer",
        tags=["Buyer auth"],
    )
    def patch(self, request):
        buyer = request.user
        serializer = BuyerUpdateSerializer(buyer, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        new_avatar_provided = "avatar_photo" in serializer.validated_data
        extra = {"avatar_processing_status": BuyerAvatarProcessingStatus.PENDING} if new_avatar_provided else {}
        serializer.save(**extra)

        if new_avatar_provided:
            process_buyer_avatar.delay(buyer.id)

        return Response(BuyerMeSerializer(buyer).data)


class BuyerRefreshView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        request=RefreshRequestSerializer,
        responses=TokenPairResponseSerializer,
        summary="Buyer token refresh",
        tags=["Buyer auth"],
    )
    def post(self, request):
        serializer = RefreshRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        payload = buyer_jwt.decode(serializer.validated_data["refreshToken"])
        if payload is None or payload.get("type") != "refresh":
            raise InvalidCredentials("Invalid or expired refresh token")

        account = Buyer.objects.filter(id=payload.get("id")).first()
        if account is None:
            raise InvalidCredentials("Account not found")
        if not account.active:
            raise exceptions.PermissionDenied("Account is inactive")

        return Response(_issue_token_pair(account))


class BuyerFavoriteProductView(APIView):
    authentication_classes = [BuyerJWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=None, responses={200: _FAVORITE_ADDED_RESPONSE},
        summary="Add product to favorites", tags=["Buyer favorites"],
    )
    def post(self, request, product_id):
        product = get_object_or_404(StoreProduct, id=product_id)
        request.user.favorite_products.add(product)
        return Response(status=status.HTTP_200_OK)

    @extend_schema(
        request=None, responses={200: _FAVORITE_REMOVED_RESPONSE},
        summary="Remove product from favorites", tags=["Buyer favorites"],
    )
    def delete(self, request, product_id):
        product = get_object_or_404(StoreProduct, id=product_id)
        request.user.favorite_products.remove(product)
        return Response(status=status.HTTP_200_OK)


class BuyerFavoriteStoreView(APIView):
    authentication_classes = [BuyerJWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=None, responses={200: _FAVORITE_ADDED_RESPONSE},
        summary="Add store to favorites", tags=["Buyer favorites"],
    )
    def post(self, request, store_id):
        store = get_object_or_404(Store, id=store_id)
        request.user.favorite_stores.add(store)
        return Response(status=status.HTTP_200_OK)

    @extend_schema(
        request=None, responses={200: _FAVORITE_REMOVED_RESPONSE},
        summary="Remove store from favorites", tags=["Buyer favorites"],
    )
    def delete(self, request, store_id):
        store = get_object_or_404(Store, id=store_id)
        request.user.favorite_stores.remove(store)
        return Response(status=status.HTTP_200_OK)


class BuyerFavoriteProductListView(APIView):
    """Buyer's favorited products, paginated - no field filtering (see products' .../get-all for that pattern)."""

    authentication_classes = [BuyerJWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=PageRequestSerializer,
        responses=paginated_serializer(FavoriteProductSerializer),
        summary="List favorite products (paginated)",
        tags=["Buyer favorites"],
    )
    def post(self, request):
        result = paginate_body(
            request.user.favorite_products.all(), request.data.get("page"), request.data.get("pageSize"),
        )
        serializer = FavoriteProductSerializer(result["items"], many=True)
        return Response({
            "items": serializer.data,
            "page": result["page"],
            "totalPages": result["totalPages"],
            "total": result["total"],
        })


class BuyerFavoriteStoreListView(APIView):
    """Buyer's favorited stores, paginated - no field filtering (see products' .../get-all for that pattern)."""

    authentication_classes = [BuyerJWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=PageRequestSerializer,
        responses=paginated_serializer(StoreSerializer),
        summary="List favorite stores (paginated)",
        tags=["Buyer favorites"],
    )
    def post(self, request):
        result = paginate_body(
            request.user.favorite_stores.all(), request.data.get("page"), request.data.get("pageSize"),
        )
        serializer = StoreSerializer(result["items"], many=True)
        return Response({
            "items": serializer.data,
            "page": result["page"],
            "totalPages": result["totalPages"],
            "total": result["total"],
        })

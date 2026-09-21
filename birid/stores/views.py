from drf_spectacular.utils import extend_schema
from rest_framework import exceptions
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.exceptions import InvalidCredentials
from core.serializers import LoginRequestSerializer, RefreshRequestSerializer, TokenPairResponseSerializer

from .authentication import StoreAdminJWTAuthentication
from .models import StoreAdmin
from .security import store_admin_jwt
from .serializers import StoreAdminMeSerializer


def _issue_token_pair(account: StoreAdmin) -> dict:
    payload = {"id": account.id, "login": account.login, "store_id": account.store_id}
    return {
        "accessToken": store_admin_jwt.create_access_token(payload),
        "refreshToken": store_admin_jwt.create_refresh_token(payload),
    }


class StoreAdminLoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        request=LoginRequestSerializer,
        responses=TokenPairResponseSerializer,
        summary="Store admin login",
        tags=["stores-auth"],
    )
    def post(self, request):
        serializer = LoginRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        account = StoreAdmin.objects.filter(login=serializer.validated_data["login"]).first()
        if account is None or not account.check_password(serializer.validated_data["password"]):
            raise InvalidCredentials()
        if not account.active:
            raise exceptions.PermissionDenied("Account is inactive")

        return Response(_issue_token_pair(account))


class StoreAdminMeView(APIView):
    authentication_classes = [StoreAdminJWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses=StoreAdminMeSerializer,
        summary="Current store admin",
        tags=["stores-auth"],
    )
    def get(self, request):
        return Response(StoreAdminMeSerializer(request.user).data)


class StoreAdminRefreshView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        request=RefreshRequestSerializer,
        responses=TokenPairResponseSerializer,
        summary="Store admin token refresh",
        tags=["stores-auth"],
    )
    def post(self, request):
        serializer = RefreshRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        payload = store_admin_jwt.decode(serializer.validated_data["refreshToken"])
        if payload is None or payload.get("type") != "refresh":
            raise InvalidCredentials("Invalid or expired refresh token")

        account = StoreAdmin.objects.filter(id=payload.get("id")).first()
        if account is None:
            raise InvalidCredentials("Account not found")
        if not account.active:
            raise exceptions.PermissionDenied("Account is inactive")

        return Response(_issue_token_pair(account))

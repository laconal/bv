from django.conf import settings

from core.jwt import JWTIssuer

buyer_jwt = JWTIssuer(
    private_key_path=settings.BUYER_JWT["PRIVATE_KEY_PATH"],
    public_key_path=settings.BUYER_JWT["PUBLIC_KEY_PATH"],
    algorithm=settings.JWT_ALGORITHM,
    access_ttl=settings.BUYER_JWT["ACCESS_TOKEN_EXPIRE_SECONDS"],
    refresh_ttl=settings.BUYER_JWT["REFRESH_TOKEN_EXPIRE_SECONDS"],
)
